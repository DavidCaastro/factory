#!/usr/bin/env python3
"""
PIV/OAC Documentation Validator
Validates Markdown files for consistency and vocabulary compliance.

Usage:
    python scripts/validate_docs.py [file1.md file2.md ...]  # validate specific files
    python scripts/validate_docs.py --all                    # validate all .md files
    python scripts/validate_docs.py --staged                 # validate git-staged .md files

Exit codes:
    0 — all checks passed (or only BAJO/MEDIO issues found)
    1 — CRÍTICO or ALTO issues found (pre-commit should block)
"""

import re
import sys
import io
import subprocess
from pathlib import Path

# Ensure stdout uses UTF-8 (needed on Windows with cp1252 default encoding)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
else:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Configuration ──────────────────────────────────────────────────────────────

# Use cwd() — scripts must be run from repo root (same as git operations)
REPO_ROOT = Path.cwd()

# Files excluded from vocabulary checks (deprecated/migration docs that reference old terms)
VOCAB_EXCLUDED_FILES = {
    "engram/session_learning.md",
    "engram\\session_learning.md",
    "docs/ROADMAP_PRODUCCION.md",
    "docs\\ROADMAP_PRODUCCION.md",
}

# Lines containing these words are skipped for vocab checks (migration/deprecation context)
VOCAB_SKIP_CONTEXT = re.compile(
    r'\b(obsoleto|deprecated|DEPRECADO|fue reemplazado|ahora es|migration|reemplazar|RQs?)\b',
    re.IGNORECASE
)

# Vocabulary violations: (pattern, replacement, severity, description)
VOCAB_VIOLATIONS = [
    (
        r"\bVETO_CASCADA\b",
        "SECURITY_VETO",
        "ALTO",
        "Termino obsoleto: usar SECURITY_VETO"
    ),
    (
        r"engram/core/session_learning\.md",
        ".piv/active/<objetivo-id>.json",
        "ALTO",
        "Checkpoint destino obsoleto: usar .piv/active/<objetivo>.json"
    ),
    (
        r"\bproject_spec\.md\b",
        "specs/active/INDEX.md",
        "BAJO",
        "Referencia obsoleta: usar specs/active/INDEX.md"
    ),
    (
        r"\bEN_PROGRESO\b",
        "EN_EJECUCION (tareas) / EN_PROGRESO (solo RQs)",
        "MEDIO",
        "EN_PROGRESO solo valido como estado de RQs - para tareas usar EN_EJECUCION"
    ),
]

# Gate 2b completeness: files mentioning Gate 2b must include all three agents
GATE_2B_AGENTS = ["SecurityAgent", "AuditAgent", "StandardsAgent"]


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_staged_md_files() -> list[Path]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True, text=True
    )
    return [
        REPO_ROOT / f for f in result.stdout.splitlines()
        if f.endswith(".md") and (REPO_ROOT / f).exists()
    ]


def get_all_md_files() -> list[Path]:
    excluded = {".git", "worktrees", "node_modules", "__pycache__"}
    return [
        p for p in REPO_ROOT.rglob("*.md")
        if not any(part in excluded for part in p.parts)
    ]


def strip_code_blocks(content: str) -> str:
    """Remove fenced code blocks and inline code to avoid false positives."""
    # Remove fenced code blocks (``` ... ```)
    content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    # Remove inline code (`...`)
    content = re.sub(r'`[^`\n]+`', '`REDACTED`', content)
    return content


def check_file_references(path: Path, content: str) -> list[dict]:
    """Check that markdown links [text](relative_path) resolve to existing files.
    Only checks links outside code blocks."""
    issues = []
    clean = strip_code_blocks(content)
    for m in re.finditer(r'\[([^\]]+)\]\(([^)#\s]+)(?:#[^)]*)?\)', clean):
        target = m.group(2).strip()
        # Skip URLs, anchors-only, and placeholder-style values
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        if not target.endswith(".md") and "/" not in target:
            continue  # skip non-path-like targets
        resolved = (path.parent / target).resolve()
        if not resolved.exists():
            issues.append({
                "severity": "ALTO",
                "type": "REF_ROTA",
                "file": str(path.relative_to(REPO_ROOT)),
                "detail": f"Referencia rota: [{m.group(1)}]({target})",
            })
    return issues


def check_vocabulary(path: Path, content: str) -> list[dict]:
    """Check for deprecated vocabulary terms (skips code blocks and migration context)."""
    rel = str(path.relative_to(REPO_ROOT))
    if rel in VOCAB_EXCLUDED_FILES:
        return []
    issues = []
    # Remove fenced code blocks before checking vocabulary
    clean = re.sub(r'```.*?```', '', content, flags=re.DOTALL)
    lines = clean.splitlines()
    for i, line in enumerate(lines, 1):
        # Skip lines that are documenting the deprecated term itself (migration/deprecation context)
        if VOCAB_SKIP_CONTEXT.search(line):
            continue
        for pattern, replacement, severity, description in VOCAB_VIOLATIONS:
            if re.search(pattern, line):
                issues.append({
                    "severity": severity,
                    "type": "VOCABULARIO",
                    "file": rel,
                    "detail": f"Linea {i}: {description}",
                    "line": line.strip()[:100],
                })
    return issues


def check_duplicate_sections(path: Path, content: str) -> list[dict]:
    issues = []
    section_numbers = re.findall(r'^##\s+(\d+)\.', content, re.MULTILINE)
    seen = {}
    for n in section_numbers:
        if n in seen:
            issues.append({
                "severity": "MEDIO",
                "type": "SECCIÓN_DUPLICADA",
                "file": str(path.relative_to(REPO_ROOT)),
                "detail": f"Número de sección duplicado: §{n}",
            })
        seen[n] = True
    return issues


def check_gate_2b_completeness(path: Path, content: str) -> list[dict]:
    """Only check files that define Gate 2b responsibilities (have 'Responsables:' near Gate 2b)."""
    issues = []
    # Only apply to files that define gate agents explicitly (contracts/, registry/, CLAUDE.md, agent.md)
    rel = str(path.relative_to(REPO_ROOT))
    if not any(rel.startswith(p) for p in ("contracts", "registry", "CLAUDE.md", "agent.md")):
        return issues
    # Look for Responsables: pattern near Gate 2b (definition context)
    for m in re.finditer(r'(?:Gate 2b|Gate2b).{0,50}(?:\n[^\n]*){0,3}.*?Responsables:.{0,200}',
                         content, re.DOTALL | re.IGNORECASE):
        section = m.group(0)
        missing = [a for a in GATE_2B_AGENTS if a not in section]
        if missing:
            issues.append({
                "severity": "ALTO",
                "type": "GATE_2B_INCOMPLETO",
                "file": rel,
                "detail": f"Gate 2b: agentes faltantes en definicion: {', '.join(missing)}",
            })
            break
    return issues


def validate_file(path: Path) -> list[dict]:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return [{"severity": "MEDIO", "type": "LECTURA", "file": str(path), "detail": str(e)}]

    issues = []
    issues += check_vocabulary(path, content)
    issues += check_file_references(path, content)

    issues += check_duplicate_sections(path, content)
    issues += check_gate_2b_completeness(path, content)
    return issues


# ── Main ───────────────────────────────────────────────────────────────────────

SEVERITY_ORDER = {"CRÍTICO": 0, "ALTO": 1, "MEDIO": 2, "BAJO": 3}


def main() -> int:
    args = sys.argv[1:]

    if "--staged" in args or not args:
        files = get_staged_md_files()
        mode = "STAGED"
    elif "--all" in args:
        files = get_all_md_files()
        mode = "ALL"
    else:
        files = [Path(a) for a in args if a.endswith(".md")]
        mode = "EXPLICIT"

    if not files:
        print(f"[validate_docs] No hay archivos .md para validar ({mode}).")
        return 0

    print(f"\n[validate_docs] Validando {len(files)} archivo(s) ({mode})...")

    all_issues: list[dict] = []
    for f in files:
        all_issues += validate_file(f)

    if not all_issues:
        print("[validate_docs] OK: Sin issues encontrados.\n")
        return 0

    # Sort by severity then file
    all_issues.sort(key=lambda x: (SEVERITY_ORDER.get(x["severity"], 9), x["file"]))

    counts = {"CRÍTICO": 0, "ALTO": 0, "MEDIO": 0, "BAJO": 0}
    for issue in all_issues:
        s = issue["severity"]
        counts[s] = counts.get(s, 0) + 1
        prefix = f"  [{s}]"
        print(f"{prefix:12} {issue['file']} - {issue['type']}: {issue['detail']}")
        if "line" in issue:
            print(f"{'':12}   > {issue['line']}")

    print(
        f"\n[validate_docs] Resumen: "
        f"{counts['CRÍTICO']} CRÍTICO, {counts['ALTO']} ALTO, "
        f"{counts['MEDIO']} MEDIO, {counts['BAJO']} BAJO\n"
    )

    if counts["CRÍTICO"] > 0 or counts["ALTO"] > 0:
        print("[validate_docs] BLOQUEADO: issues CRÍTICO/ALTO deben resolverse antes del commit.\n")
        return 1

    print("[validate_docs] OK: solo issues MEDIO/BAJO — commit permitido.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
