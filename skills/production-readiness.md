# skill: production-readiness

> Cargado por: StandardsAgent (Gate 3), AuditAgent (FASE 8), MasterOrchestrator (evaluación pre-release)
> Activación: automática cuando `execution_mode: DEVELOPMENT` y Gate 3 en curso

---

## 1. Propósito

Define el proceso de evaluación de preparación para producción que se ejecuta en dos momentos:

1. **Gate 3 (StandardsAgent)** — checklist bloqueante antes del merge staging → main
2. **FASE 8 (AuditAgent)** — auditoría post-merge como parte del TechSpecSheet

El resultado es una puntuación 0–100 por dimensión y un veredicto `PR_GATE_PASS` / `PR_GATE_FAIL`.

---

## 2. Dimensiones y comandos deterministas

Cada dimensión tiene:
- Una herramienta determinista que emite el valor real (no estimado)
- Un umbral mínimo para aprobar
- Comportamiento si la herramienta no está disponible (`BLOQUEADO_POR_HERRAMIENTA`)

### D1 — Cobertura de tests (`peso 15%`)

```bash
cd <repo_root>
pytest --cov=<src_dir> --cov-report=term-missing --cov-fail-under=80 -q
```

**Umbral:** ≥ 80%
**Evidencia requerida:** línea `TOTAL ... XX%` del output de pytest-cov
**Si herramienta no disponible:** BLOQUEADO — no se admite estimación

---

### D2 — Calidad de código: lint y complejidad (`peso 10%`)

```bash
# Lint
ruff check <src_dir> --output-format=json > /tmp/ruff_out.json
python -c "import json,sys; d=json.load(open('/tmp/ruff_out.json')); print(f'VIOLATIONS: {len(d)}')"

# Complejidad ciclomática (si lizard disponible)
lizard <src_dir> -C 10 --csv | tail -n +2 | awk -F',' '$3>10 {count++} END {print "COMPLEX_FUNCS: " count+0}'
```

**Umbral:** 0 violaciones de error/warning ruff; complejidad máx. 10 por función
**Si ruff no disponible:** BLOQUEADO

---

### D3 — Seguridad estática (`peso 12%`)

```bash
# Secretos hardcodeados
grep -r -i -E "(password|secret|api_key|token)\s*=\s*['\"][^'\"]{8,}" \
  --include="*.py" --include="*.js" --include="*.ts" \
  --exclude-dir=".git" --exclude-dir="tests" <repo_root> \
  | grep -v "os\.environ\|os\.getenv\|settings\.\|config\.\|test\|example\|EXAMPLE" \
  | wc -l

# CVEs en dependencias Python
pip-audit --format=json 2>/dev/null | python -c "
import json,sys
data=json.load(sys.stdin) if not sys.stdin.isatty() else {'dependencies':[]}
vulns=[v for d in data.get('dependencies',[]) for v in d.get('vulns',[])]
critical_high=[v for v in vulns if v.get('fix_versions')]
print(f'VULNS_TOTAL: {len(vulns)}')
print(f'VULNS_FIXABLE: {len(critical_high)}')
"

# Semgrep (si disponible)
semgrep --config=auto --json <src_dir> 2>/dev/null | python -c "
import json,sys
try:
  d=json.load(sys.stdin)
  errors=[r for r in d.get('results',[]) if r.get('extra',{}).get('severity') in ('ERROR','WARNING')]
  print(f'SEMGREP_FINDINGS: {len(errors)}')
except:
  print('SEMGREP_FINDINGS: BLOQUEADO_POR_HERRAMIENTA')
"
```

**Umbral:** 0 secretos detectados, 0 CVEs fixables, 0 findings semgrep severity ERROR
**Si pip-audit no disponible:** BLOQUEADO en esta sub-dimensión

---

### D4 — Empaquetado y distribución (`peso 12%`)

```bash
# Verificar que pyproject.toml / setup.py existe y es válido
python -c "
import importlib.metadata, sys
try:
  v = importlib.metadata.version('<package_name>')
  print(f'INSTALLED_VERSION: {v}')
except importlib.metadata.PackageNotFoundError:
  print('INSTALLED_VERSION: NOT_FOUND')
  sys.exit(1)
"

# Verificar entrada en PyPI (requiere httpx o requests)
python -c "
import urllib.request, json, sys
pkg = '<package_name>'
try:
  with urllib.request.urlopen(f'https://pypi.org/pypi/{pkg}/json', timeout=10) as r:
    data = json.loads(r.read())
    latest = data['info']['version']
    print(f'PYPI_VERSION: {latest}')
except Exception as e:
  print(f'PYPI_CHECK: FAIL ({e})')
"

# Verificar CLI entry point
<cli_command> --help > /dev/null 2>&1 && echo "CLI_ENTRY: OK" || echo "CLI_ENTRY: FAIL"
```

**Umbral:** paquete instalable, versión publicada en PyPI (o en registro privado), CLI funcional
**Substitución:** si no hay PyPI → verificar instalable desde `pip install -e .` o `pip install .`

---

### D5 — Documentación (`peso 10%`)

```bash
# README.md presente con secciones mínimas
for section in "install" "usage" "## " "license"; do
  grep -qi "$section" <repo_root>/README.md \
    && echo "README_${section^^}: OK" \
    || echo "README_${section^^}: MISSING"
done

# API reference (docs/sdk-api.md o OpenAPI)
ls <repo_root>/docs/sdk-api.md 2>/dev/null && echo "API_REF: OK" || \
  ls <repo_root>/docs/api.md 2>/dev/null && echo "API_REF: OK" || \
  curl -s <base_url>/openapi.json > /dev/null 2>&1 && echo "API_REF: OPENAPI_LIVE" || \
  echo "API_REF: MISSING"

```

**Umbral:** README con ≥4 secciones identificables, referencia de API presente

---

### D6 — CI/CD pipeline (`peso 8%`)

```bash
# GitHub Actions: verificar que el workflow existe y que el último run pasó
# (Ejecutar desde scripts/check_ci.py o via gh CLI)
gh run list --branch main --limit 1 --json conclusion,status \
  | python -c "import json,sys; d=json.load(sys.stdin); print(f'CI_STATUS: {d[0][\"conclusion\"] if d else \"NO_RUNS\"}')"

# Pre-push hook activo
test -x <repo_root>/.git/hooks/pre-push \
  && echo "PRE_PUSH_HOOK: OK" || echo "PRE_PUSH_HOOK: MISSING"
```

**Umbral:** último run en main = `success`, pre-push hook presente y ejecutable

---

### D7 — Observabilidad (`peso 8%`)

```bash
# Módulo de telemetría importable
python -c "
from <package>.telemetry import setup_tracing
print('TELEMETRY_MODULE: OK')
" 2>/dev/null || echo "TELEMETRY_MODULE: MISSING"

# Variables de entorno de observabilidad documentadas
grep -c "OTEL_\|PIV_OAC_TELEMETRY" <repo_root>/docs/deployment.md 2>/dev/null \
  && echo "OTEL_VARS_DOCUMENTED: OK" || echo "OTEL_VARS_DOCUMENTED: MISSING"
```

**Umbral:** módulo de telemetría importable (puede ser no-op sin OTel instalado), variables documentadas

---

### D8 — Compliance y ética (`peso 8%`)

```bash
# LICENSE presente
ls <repo_root>/LICENSE* 2>/dev/null && echo "LICENSE: OK" || echo "LICENSE: MISSING"

# Disclaimer en entregables
grep -i "disclaimer\|legal\|compliance" <repo_root>/compliance/ -r --include="*.md" -l 2>/dev/null \
  | wc -l | xargs -I{} echo "COMPLIANCE_DOCS: {}"
```

**Umbral:** LICENSE presente; si compliance_scope != NONE → al menos 1 documento de compliance generado

---

### D9 — Checkpoint y recuperabilidad (`peso 7%`)

```bash
# CheckpointStore funciona
python -c "
from <package>.checkpoint.store import CheckpointStore
from pathlib import Path
import tempfile, sys
with tempfile.TemporaryDirectory() as d:
  store = CheckpointStore(Path(d))
  s = store.create('TEST-001', 'test')
  store.save(s)
  loaded = store.load('TEST-001')
  assert loaded.objective_id == 'TEST-001'
  print('CHECKPOINT_STORE: OK')
" 2>/dev/null || echo "CHECKPOINT_STORE: FAIL"

# CheckpointValidator funciona
python -c "
from <package>.checkpoint.validator import CheckpointValidator
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as d:
  p = Path(d)
  (p / '.git').mkdir()
  v = CheckpointValidator(repo_root=p)
  r = v.validate_all()
  assert r.passed
  print('CHECKPOINT_VALIDATOR: OK')
" 2>/dev/null || echo "CHECKPOINT_VALIDATOR: FAIL"
```

**Umbral:** CheckpointStore y CheckpointValidator operacionales

---

### D10 — Modularidad (`peso 5%`)

```bash
# Verificar que los módulos core son importables independientemente
python -c "
modules = [
  '<package>.agents.base',
  '<package>.checkpoint.store',
  '<package>.dag.validator',
  '<package>.exceptions',
]
for m in modules:
  try:
    __import__(m)
    print(f'MODULE {m}: OK')
  except ImportError as e:
    print(f'MODULE {m}: FAIL ({e})')
"
```

**Umbral:** todos los módulos core importables sin errores

---

### D11 — Ecosistema y adopción (`peso 5%`)

> Esta dimensión tiene peso reducido para proyectos en fase de lanzamiento inicial.
> Evalúa únicamente indicadores objetivos y verificables.

```bash
# Contar dependencias directas que consumen el paquete (si aplica)
# En proyectos en construcción: verificar que el paquete funciona en un repo externo vacío
pip install <package_name> --dry-run 2>&1 | grep "Would install" | grep -v "already satisfied"
```

**Umbral en fase inicial (v0.x):** paquete instalable en entorno limpio sin errores de resolución

---

## 3. Proceso de evaluación automatizado

### 3.1 Script de evaluación — `scripts/check_production_readiness.py`

```python
"""
Ejecutar: python scripts/check_production_readiness.py [--threshold 70]

Evalúa las dimensiones de producción y emite PR_GATE_PASS / PR_GATE_FAIL.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

WEIGHTS: dict[str, float] = {
    "D1_coverage":       0.15,
    "D2_quality":        0.10,
    "D3_security":       0.12,
    "D4_packaging":      0.12,
    "D5_docs":           0.10,
    "D6_cicd":           0.08,
    "D7_observability":  0.08,
    "D8_compliance":     0.08,
    "D9_checkpoint":     0.07,
    "D10_modularity":    0.05,
    "D11_ecosystem":     0.05,
}

BLOCKED = "BLOQUEADO_POR_HERRAMIENTA"


@dataclass
class DimensionResult:
    id: str
    score: float  # 0.0–1.0
    blocked: bool = False
    evidence: str = ""
    issues: list[str] = field(default_factory=list)


def run(cmd: str, cwd: Path | None = None) -> tuple[int, str]:
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=cwd
    )
    return result.returncode, result.stdout + result.stderr


def check_coverage(src_dir: Path) -> DimensionResult:
    code, out = run(
        f"pytest --cov={src_dir} --cov-fail-under=80 -q --no-header 2>&1 | tail -5",
        cwd=src_dir.parent,
    )
    if "pytest" not in out and code != 0:
        return DimensionResult("D1_coverage", 0.0, blocked=True, evidence=BLOCKED)
    # Extract coverage percentage
    for line in out.splitlines():
        if "TOTAL" in line and "%" in line:
            pct_str = [t for t in line.split() if "%" in t]
            if pct_str:
                pct = float(pct_str[0].replace("%", ""))
                score = min(1.0, pct / 100.0)
                return DimensionResult("D1_coverage", score, evidence=f"Coverage: {pct:.1f}%")
    return DimensionResult("D1_coverage", 0.5, evidence="Coverage line not found in output")


def evaluate_all(repo_root: Path, src_dir: Path, threshold: float = 0.70) -> None:
    results: list[DimensionResult] = []

    results.append(check_coverage(src_dir))
    # Add remaining dimension checks here following the same pattern

    blocked = [r for r in results if r.blocked]
    scored = [r for r in results if not r.blocked]

    total_weight = sum(WEIGHTS.get(r.id, 0) for r in scored)
    if total_weight == 0:
        print("PR_GATE_FAIL — all dimensions blocked")
        sys.exit(1)

    weighted_score = sum(
        r.score * WEIGHTS.get(r.id, 0) for r in scored
    ) / total_weight

    print("\n=== PRODUCTION READINESS REPORT ===")
    for r in results:
        status = BLOCKED if r.blocked else f"{r.score*100:.0f}%"
        print(f"  {r.id:25} {status:20} {r.evidence}")

    if blocked:
        print(f"\n  BLOCKED dimensions: {[r.id for r in blocked]}")

    print(f"\n  WEIGHTED SCORE: {weighted_score*100:.1f}%  (threshold: {threshold*100:.0f}%)")

    if weighted_score >= threshold and not blocked:
        print("  VEREDICTO: PR_GATE_PASS")
    elif blocked:
        print(f"  VEREDICTO: PR_GATE_FAIL — {len(blocked)} dimension(s) blocked by missing tools")
        sys.exit(1)
    else:
        print(f"  VEREDICTO: PR_GATE_FAIL — score {weighted_score*100:.1f}% < {threshold*100:.0f}%")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=float, default=0.70)
    parser.add_argument("--src", default="piv_oac")
    args = parser.parse_args()
    evaluate_all(
        repo_root=Path(".").resolve(),
        src_dir=Path(args.src).resolve(),
        threshold=args.threshold,
    )
```

---

## 4. Integración con Gate 3

El StandardsAgent ejecuta este proceso como parte de su Gate 3 checklist:

```
[StandardsAgent — Gate 3 — Production Readiness]

1. cd <repo_root>/sdk && python ../scripts/check_production_readiness.py --threshold 0.70
2. Registrar score por dimensión en TechSpecSheet §Production Readiness
3. Si PR_GATE_FAIL:
   a. Si BLOQUEADO_POR_HERRAMIENTA: notificar al Domain Orchestrator qué herramienta instalar
   b. Si score < threshold: lista de dimensiones a mejorar con puntaje y delta requerido
4. Si PR_GATE_PASS: emitir STANDARDS_GATE_PASS con score adjunto
```

**Umbral Gate 3:** weighted score ≥ 70% sin dimensiones bloqueadas

---

## 5. Integración con CI (job adicional en piv-gate-framework.yml)

```yaml
check-production-readiness:
  name: "Check — Production Readiness Score"
  runs-on: ubuntu-latest
  needs: [gate-2b-sdk]
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: "3.11" }
    - name: Install SDK
      run: cd sdk && pip install -e ".[dev]"
    - name: Run production readiness evaluation
      run: python scripts/check_production_readiness.py --threshold 0.70 --src sdk/piv_oac
      continue-on-error: true  # Advertencia pero no bloquea en agent-configs
    - name: Upload report
      uses: actions/upload-artifact@v4
      with:
        name: production-readiness-report
        path: /tmp/pr_report.json
        if-no-files-found: ignore
```

> En rama `main` (producto), el job **sí** es bloqueante (`continue-on-error: false`).

---

## 6. Ponderaciones ajustadas por etapa del proyecto

| Etapa | D4 Packaging | D11 Ecosistema | D5 Docs | Threshold |
|---|---|---|---|---|
| Pre-alpha (v0.1.x) | 5% | 2% | 8% | 60% |
| Beta (v0.2.x–v0.9.x) | 12% | 5% | 10% | 70% |
| Stable (v1.0+) | 15% | 10% | 12% | 80% |

> Usar la fila que corresponda a la versión declarada en `pyproject.toml`.

---

## 7. Referencias cruzadas

| Documento | Relación |
|---|---|
| `contracts/evaluation.md` | Scoring 5D para outputs de agentes (complementario, no el mismo) |
| `contracts/gates.md` | Definición canónica de Gate 3 |
| `registry/standards_agent.md` | Agente ejecutor de este checklist |
| `registry/audit_agent.md` | Registra el resultado en TechSpecSheet y engram |
| `skills/observability.md` | Detalle de D7 — implementación OTel |
| `skills/product-docs.md` | Detalle de D5 — checklist de documentación |
| `metrics/sessions.md` | Destino append-only del score por sesión |
