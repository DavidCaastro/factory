"""
PIV/OAC — Production Readiness Evaluator
=========================================
Ejecutar: python scripts/check_production_readiness.py [--threshold 0.70] [--src sdk/piv_oac]

Evalúa las dimensiones de producción y emite PR_GATE_PASS / PR_GATE_FAIL.
Diseñado para ser ejecutado por StandardsAgent en Gate 3 y por CI/CD.

Dimensiones evaluadas (ver skills/production-readiness.md para detalle):
  D1  Coverage         15%
  D2  Code quality     10%
  D3  Security         12%
  D4  Packaging        12%
  D5  Documentation    10%
  D6  CI/CD             8%
  D7  Observability     8%
  D8  Compliance        8%
  D9  Checkpoint        7%
  D10 Modularity        5%
  D11 Ecosystem         5%
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

BLOCKED = "BLOQUEADO_POR_HERRAMIENTA"

# Weights sum to 1.0
WEIGHTS: dict[str, float] = {
    "D1_coverage":      0.15,
    "D2_quality":       0.10,
    "D3_security":      0.12,
    "D4_packaging":     0.12,
    "D5_docs":          0.10,
    "D6_cicd":          0.08,
    "D7_observability": 0.08,
    "D8_compliance":    0.08,
    "D9_checkpoint":    0.07,
    "D10_modularity":   0.05,
    "D11_ecosystem":    0.05,
}


@dataclass
class DimensionResult:
    id: str
    score: float          # 0.0–1.0; -1.0 means blocked
    blocked: bool = False
    evidence: str = ""
    issues: list[str] = field(default_factory=list)

    @property
    def display_score(self) -> str:
        return BLOCKED if self.blocked else f"{self.score * 100:.0f}%"


def _run(cmd: str, cwd: Path | None = None, timeout: int = 60) -> tuple[int, str]:
    """Run shell command, return (returncode, combined_output)."""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            cwd=str(cwd) if cwd else None, timeout=timeout,
        )
        return r.returncode, r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return 1, f"TIMEOUT after {timeout}s"
    except Exception as e:
        return 1, str(e)


# ── D1: Coverage ──────────────────────────────────────────────────────────────

def check_d1_coverage(repo_root: Path, src_dir: Path) -> DimensionResult:
    code, out = _run(
        f"pytest --cov={src_dir.name} --cov-report=term-missing -q --no-header 2>&1",
        cwd=src_dir.parent,
    )
    # Look for TOTAL line
    for line in out.splitlines():
        if line.strip().startswith("TOTAL") and "%" in line:
            parts = line.split()
            pct_str = next((p for p in parts if p.endswith("%")), None)
            if pct_str:
                pct = float(pct_str.rstrip("%"))
                score = min(1.0, pct / 100.0)
                issues = [] if pct >= 80 else [f"Coverage {pct:.1f}% < 80% threshold"]
                return DimensionResult("D1_coverage", score,
                                       evidence=f"pytest-cov: {pct:.1f}%", issues=issues)
    if "pytest" not in out and code != 0:
        return DimensionResult("D1_coverage", 0.0, blocked=True, evidence=BLOCKED)
    return DimensionResult("D1_coverage", 0.5, evidence="Coverage line not found")


# ── D2: Code quality ──────────────────────────────────────────────────────────

def check_d2_quality(src_dir: Path) -> DimensionResult:
    code, out = _run(f"ruff check {src_dir} --output-format=json 2>&1")
    if code not in (0, 1) or "command not found" in out.lower():
        return DimensionResult("D2_quality", 0.0, blocked=True, evidence=BLOCKED)
    try:
        findings = json.loads(out) if out.strip().startswith("[") else []
        errors = [f for f in findings if f.get("code", "").startswith(("E", "F", "W"))]
        score = 1.0 if not errors else max(0.0, 1.0 - len(errors) / 20)
        issues = [f"ruff: {len(errors)} violations"] if errors else []
        return DimensionResult("D2_quality", score,
                               evidence=f"ruff: {len(errors)} violations", issues=issues)
    except json.JSONDecodeError:
        score = 1.0 if code == 0 else 0.3
        return DimensionResult("D2_quality", score, evidence=f"ruff exit={code}")


# ── D3: Security ──────────────────────────────────────────────────────────────

def check_d3_security(repo_root: Path, src_dir: Path) -> DimensionResult:
    issues: list[str] = []
    score = 1.0

    # Secrets scan
    _, out = _run(
        r'grep -r -i -E "(password|secret|api_key)\s*=\s*[' + r"'\"" +
        r'][^' + r"'\"]" + r'{8,}" '
        r'--include="*.py" --exclude-dir=".git" --exclude-dir="tests" ' +
        str(src_dir) + r' | grep -v "os\.environ\|os\.getenv\|test\|example" | wc -l'
    )
    secrets_count = int(out.strip()) if out.strip().isdigit() else 0
    if secrets_count > 0:
        issues.append(f"{secrets_count} potential hardcoded secrets")
        score -= 0.5

    # pip-audit
    code, out = _run("pip-audit --format=json 2>&1", timeout=90)
    if "command not found" in out.lower() or code == 127:
        issues.append("pip-audit not available")
        score = max(0.0, score - 0.1)
    else:
        try:
            data = json.loads(out) if out.strip().startswith("{") else {"dependencies": []}
            vulns = [v for d in data.get("dependencies", []) for v in d.get("vulns", [])]
            fixable = [v for v in vulns if v.get("fix_versions")]
            if fixable:
                issues.append(f"pip-audit: {len(fixable)} fixable CVEs")
                score -= 0.4
        except json.JSONDecodeError:
            pass

    return DimensionResult("D3_security", max(0.0, score),
                           evidence=f"secrets={secrets_count}, issues={len(issues)}",
                           issues=issues)


# ── D4: Packaging ─────────────────────────────────────────────────────────────

def check_d4_packaging(repo_root: Path, package_name: str) -> DimensionResult:
    issues: list[str] = []
    score = 0.0

    # Importable
    code, _ = _run(f'python -c "import {package_name}; print(\"OK\")"')
    if code == 0:
        score += 0.4
    else:
        issues.append(f"Package {package_name!r} not importable")

    # pyproject.toml / setup.py
    has_pyproject = (repo_root / "sdk" / "pyproject.toml").exists() or \
                    (repo_root / "pyproject.toml").exists()
    if has_pyproject:
        score += 0.3
    else:
        issues.append("No pyproject.toml found")

    # PyPI check
    try:
        with urllib.request.urlopen(
            f"https://pypi.org/pypi/{package_name.replace('_', '-')}/json", timeout=10
        ) as r:
            data = json.loads(r.read())
            latest = data["info"]["version"]
            score += 0.3
            evidence = f"PyPI: {latest}"
    except Exception:
        issues.append("Package not found on PyPI (may be private)")
        evidence = "PyPI: not found"
        score += 0.1  # partial credit if importable from local install

    return DimensionResult("D4_packaging", min(1.0, score), evidence=evidence, issues=issues)


# ── D5: Documentation ────────────────────────────────────────────────────────

def check_d5_docs(repo_root: Path) -> DimensionResult:
    score = 0.0
    issues: list[str] = []
    evidence_parts: list[str] = []

    checks = {
        "README": (repo_root / "sdk" / "README.md").exists() or (repo_root / "README.md").exists(),
        "API_REF": (repo_root / "docs" / "sdk-api.md").exists() or (repo_root / "docs" / "api.md").exists(),
        "QUICKSTART": (repo_root / "docs" / "tutorials" / "quickstart.md").exists(),
        "TUTORIAL_L2": (repo_root / "docs" / "TUTORIAL_LEVEL2.md").exists(),
        "DEPLOYMENT": (repo_root / "docs" / "deployment.md").exists(),
    }

    for name, present in checks.items():
        weight = 0.3 if name == "README" else 0.175
        if present:
            score += weight
            evidence_parts.append(f"{name}:OK")
        else:
            issues.append(f"Missing: {name}")
            evidence_parts.append(f"{name}:MISSING")

    return DimensionResult("D5_docs", min(1.0, score),
                           evidence=", ".join(evidence_parts), issues=issues)


# ── D6: CI/CD ─────────────────────────────────────────────────────────────────

def check_d6_cicd(repo_root: Path) -> DimensionResult:
    score = 0.0
    issues: list[str] = []

    # GitHub Actions workflow exists
    workflows = list((repo_root / ".github" / "workflows").glob("*.yml")) if \
        (repo_root / ".github" / "workflows").exists() else []
    if workflows:
        score += 0.5
    else:
        issues.append("No GitHub Actions workflows found")

    # Pre-push hook
    hook = repo_root / ".git" / "hooks" / "pre-push"
    if hook.exists() and hook.stat().st_mode & 0o111:
        score += 0.3
    else:
        issues.append("pre-push hook missing or not executable")

    # pyproject.toml has coverage threshold
    pyproject = repo_root / "sdk" / "pyproject.toml"
    if pyproject.exists() and "fail_under" in pyproject.read_text(encoding="utf-8"):
        score += 0.2
    else:
        issues.append("No coverage fail_under in pyproject.toml")

    return DimensionResult("D6_cicd", min(1.0, score),
                           evidence=f"{len(workflows)} workflow(s)", issues=issues)


# ── D7: Observability ────────────────────────────────────────────────────────

def check_d7_observability(repo_root: Path, package_name: str) -> DimensionResult:
    score = 0.0
    issues: list[str] = []

    # Telemetry module importable
    code, _ = _run(f'python -c "from {package_name}.telemetry import setup_tracing; print(\'OK\')"')
    if code == 0:
        score += 0.6
    else:
        # Check if module exists even without OTel installed
        code2, _ = _run(f'python -c "import {package_name}.telemetry"')
        if code2 == 0:
            score += 0.4
        else:
            issues.append("telemetry module not importable")

    # OTel optional dep declared
    pyproject = repo_root / "sdk" / "pyproject.toml"
    if pyproject.exists() and "opentelemetry" in pyproject.read_text(encoding="utf-8"):
        score += 0.4
    else:
        issues.append("opentelemetry not declared as optional dep")

    return DimensionResult("D7_observability", min(1.0, score),
                           evidence=f"score={score:.1f}", issues=issues)


# ── D8: Compliance ────────────────────────────────────────────────────────────

def check_d8_compliance(repo_root: Path) -> DimensionResult:
    score = 0.0
    issues: list[str] = []

    # LICENSE
    licenses = list(repo_root.glob("LICENSE*"))
    if licenses:
        score += 0.5
    else:
        issues.append("No LICENSE file")

    # Compliance docs
    compliance_dir = repo_root / "compliance"
    if compliance_dir.exists() and list(compliance_dir.rglob("*.md")):
        score += 0.3
    else:
        issues.append("No compliance/ documents (acceptable for pre-alpha)")

    # DISCLAIMER in SDK
    init_file = repo_root / "sdk" / "piv_oac" / "agents" / "compliance.py"
    if init_file.exists() and "DISCLAIMER" in init_file.read_text(encoding="utf-8"):
        score += 0.2

    return DimensionResult("D8_compliance", min(1.0, score),
                           evidence=f"license={'yes' if licenses else 'no'}", issues=issues)


# ── D9: Checkpoint ────────────────────────────────────────────────────────────

def check_d9_checkpoint(package_name: str) -> DimensionResult:
    code, out = _run(f"""python -c "
from {package_name}.checkpoint.store import CheckpointStore
from {package_name}.checkpoint.validator import CheckpointValidator
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as d:
    p = Path(d)
    store = CheckpointStore(p)
    s = store.create('TEST-001', 'test')
    store.save(s)
    loaded = store.load('TEST-001')
    assert loaded.objective_id == 'TEST-001'
    (p / '.git').mkdir()
    v = CheckpointValidator(repo_root=p)
    r = v.validate_all()
    assert r.passed
    print('OK')
" """)
    if code == 0 and "OK" in out:
        return DimensionResult("D9_checkpoint", 1.0, evidence="CheckpointStore+Validator: OK")
    return DimensionResult("D9_checkpoint", 0.0,
                           issues=["Checkpoint subsystem failed"],
                           evidence=out.strip()[:200])


# ── D10: Modularity ──────────────────────────────────────────────────────────

def check_d10_modularity(package_name: str) -> DimensionResult:
    core_modules = [
        f"{package_name}.agents.base",
        f"{package_name}.checkpoint.store",
        f"{package_name}.dag.validator",
        f"{package_name}.exceptions",
        f"{package_name}.cli.main",
    ]
    ok = 0
    issues = []
    for m in core_modules:
        c, _ = _run(f'python -c "import {m}"')
        if c == 0:
            ok += 1
        else:
            issues.append(f"Cannot import {m}")
    score = ok / len(core_modules)
    return DimensionResult("D10_modularity", score,
                           evidence=f"{ok}/{len(core_modules)} core modules importable",
                           issues=issues)


# ── D11: Ecosystem ────────────────────────────────────────────────────────────

def check_d11_ecosystem(package_name: str) -> DimensionResult:
    """Minimal check: installable in a clean env (dry-run)."""
    score = 0.5  # Base: project exists and is importable
    issues: list[str] = []

    pkg_dash = package_name.replace("_", "-")
    code, out = _run(f"pip install {pkg_dash} --dry-run 2>&1", timeout=30)
    if code == 0:
        score = 1.0
    else:
        issues.append("Package not installable via pip (may be in development mode)")
        score = 0.5

    return DimensionResult("D11_ecosystem", score,
                           evidence="pip dry-run: " + ("OK" if code == 0 else "local-only"),
                           issues=issues)


# ── Main ──────────────────────────────────────────────────────────────────────

def evaluate_all(
    repo_root: Path,
    src_dir: Path,
    package_name: str,
    threshold: float = 0.70,
    output_json: Path | None = None,
) -> bool:
    results: list[DimensionResult] = [
        check_d1_coverage(repo_root, src_dir),
        check_d2_quality(src_dir),
        check_d3_security(repo_root, src_dir),
        check_d4_packaging(repo_root, package_name),
        check_d5_docs(repo_root),
        check_d6_cicd(repo_root),
        check_d7_observability(repo_root, package_name),
        check_d8_compliance(repo_root),
        check_d9_checkpoint(package_name),
        check_d10_modularity(package_name),
        check_d11_ecosystem(package_name),
    ]

    blocked = [r for r in results if r.blocked]
    scored = [r for r in results if not r.blocked]

    total_weight = sum(WEIGHTS.get(r.id, 0) for r in scored)
    weighted_score = (
        sum(r.score * WEIGHTS.get(r.id, 0) for r in scored) / total_weight
        if total_weight > 0 else 0.0
    )

    print("\n" + "=" * 60)
    print("  PIV/OAC PRODUCTION READINESS REPORT")
    print("=" * 60)
    for r in results:
        prefix = "[BLOCKED]" if r.blocked else f"[{r.score*100:5.1f}%]"
        print(f"  {r.id:25} {prefix:12} {r.evidence}")
        for issue in r.issues:
            print(f"    !  {issue}")

    print("-" * 60)
    if blocked:
        print(f"  BLOCKED dimensions    : {[r.id for r in blocked]}")
    print(f"  Weighted score        : {weighted_score * 100:.1f}% (threshold: {threshold * 100:.0f}%)")
    print("=" * 60)

    passed = weighted_score >= threshold and not blocked
    print(f"  VEREDICTO: {'PR_GATE_PASS' if passed else 'PR_GATE_FAIL'}")
    print("=" * 60 + "\n")

    if output_json:
        report = {
            "weighted_score": weighted_score,
            "threshold": threshold,
            "passed": passed,
            "dimensions": [
                {
                    "id": r.id,
                    "score": r.score,
                    "blocked": r.blocked,
                    "evidence": r.evidence,
                    "issues": r.issues,
                }
                for r in results
            ],
        }
        output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PIV/OAC Production Readiness Evaluator")
    parser.add_argument("--threshold", type=float, default=0.70, help="Pass threshold (0-1)")
    parser.add_argument("--src", default="piv_oac", help="Source directory name")
    parser.add_argument("--package", default="piv_oac", help="Python package name")
    parser.add_argument("--output-json", default=None, help="Path to write JSON report")
    args = parser.parse_args()

    repo = Path(".").resolve()
    src = (repo / "sdk" / args.src) if (repo / "sdk" / args.src).exists() else Path(args.src).resolve()

    output_path = Path(args.output_json) if args.output_json else None
    passed = evaluate_all(
        repo_root=repo,
        src_dir=src,
        package_name=args.package,
        threshold=args.threshold,
        output_json=output_path,
    )
    sys.exit(0 if passed else 1)
