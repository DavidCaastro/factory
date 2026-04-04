# SKILL: CI Loop — Ejecución Dinámica Iterativa Pre-Gate-2b
> Skill de carga perezosa. Cargar por: StandardsAgent (pre-Gate-2b), Domain Orchestrator (FASE 6).
> Versión: 1.0 | Introducido en: audit point post-OBJ-004

## Propósito

El CI Loop garantiza que **ningún diff llega al Gate 2b con tests fallando o cobertura insuficiente**.
Es la capa de ejecución dinámica que complementa la revisión estática (LLM) del gate.

**Principio:** Un gate que aprueba código sin haber ejecutado sus tests es inválido.
El CI Loop convierte ese principio en un protocolo obligatorio con estados binarios verificables.

---

## Cuándo Ejecutar

**Trigger obligatorio:** Domain Orchestrator, tras recibir `GATE_1_APROBADO` de CoherenceAgent,
antes de invocar Gate 2b (Security + Audit + StandardsAgent).

```
Gate 1 APROBADO
      │
      ▼
[CI LOOP — obligatorio]
      │
   LOOP_GREEN?
      │
  NO──┴──SÍ
  │       │
  ▼       ▼
Fix     Gate 2b
loop    (procede)
```

**Ejecuta en:** worktree de `feature/<tarea>` (rama integrada, post-merge de subramas de expertos).
**Responsable del loop:** StandardsAgent.
**Responsable de correcciones:** SpecialistAgent del dominio (rol TestWriter o CodeFixer).

---

## Taxonomía de Estados — Tres Estados Distintos

> **Crítico:** confundir estos tres estados es el error de diseño que este skill corrige.

| Estado | Causa | Acción |
|---|---|---|
| `TOOL_NOT_EXECUTABLE` | pytest/coverage no instalado, entorno roto, ruta incorrecta | `BLOQUEADO_POR_HERRAMIENTA` — detener, notificar al Domain Orchestrator. **No es fallo de tests.** |
| `TEST_FAILURE` | pytest ejecuta, returncode ≠ 0, uno o más tests fallan | Activar Fix Loop → SpecialistAgent corrige código o tests → re-ejecutar |
| `COVERAGE_GAP` | pytest ejecuta, returncode 0 (todos pasan), cobertura < umbral | Activar Coverage Loop → SpecialistAgent escribe tests adicionales → re-ejecutar |

**Regla:** `BLOQUEADO_POR_HERRAMIENTA` se emite **únicamente** ante `TOOL_NOT_EXECUTABLE`.
Un `TEST_FAILURE` o `COVERAGE_GAP` nunca produce `BLOQUEADO_POR_HERRAMIENTA` — activan el loop.

---

## Protocolo de Ejecución

### Paso 0 — Detectar umbrales desde specs

```
umbral_global    ← leer specs/active/quality.md → campo "Coverage gate en CI"
                   Si no existe → usar default: 80%
umbral_motores   ← leer specs/active/quality.md → umbral por tipo de módulo
                   Si no existe → usar default: umbral_global

Regla de precedencia: umbral en specs/quality.md > default del gate (contracts/gates.md).
El StandardsAgent NUNCA usa el umbral del gate si specs/quality.md define uno distinto.
```

### Paso 1 — Verificar que la herramienta es ejecutable

```bash
python -m pytest --version
```

- Exitcode 0 → herramienta disponible → continuar al Paso 2
- Cualquier error → emitir `TOOL_NOT_EXECUTABLE` → `BLOQUEADO_POR_HERRAMIENTA` → detener

### Paso 2 — Ejecutar pytest-cov (herramienta determinística)

```bash
# Determinar SRC_PATH desde specs/active/architecture.md (campo src_dir o estructura de módulos)
${PYTEST_CMD} --cov=${SRC_PATH} --cov-report=term-missing --cov-report=json -q 2>&1
```

Capturar obligatoriamente:
- `returncode` del proceso
- `tests_passed` / `tests_failed` / `tests_error`
- `coverage_total_pct` (del JSON report)
- `coverage_per_module` (del term-missing report — líneas sin cobertura por archivo)

### Paso 3 — Clasificar resultado

```
SI returncode != 0:
    estado = TEST_FAILURE
    gap = {tests_failed: [...], tests_error: [...]}

SINO SI coverage_total_pct < umbral_global:
    estado = COVERAGE_GAP
    gap = {modules_below_threshold: [...], uncovered_lines_per_module: {...}}

SINO:
    estado = GREEN
    → emitir LOOP_GREEN → Domain Orchestrator procede a Gate 2b
```

### Paso 4 — Fix Loop (si TEST_FAILURE o COVERAGE_GAP)

```
iteration = iteration + 1

SI iteration > MAX_ITERATIONS (3):
    emitir LOOP_EXHAUSTED
    → escalar al Master Orchestrator
    → Master presenta al usuario:
        "CI Loop agotado tras 3 iteraciones.
         Estado: <TEST_FAILURE | COVERAGE_GAP>
         Última cobertura: <pct>%
         Tests fallando: <lista>
         Opciones: A) revisar manualmente  B) reducir umbral  C) cancelar objetivo"
    → Detener. Ninguna acción automática tras LOOP_EXHAUSTED.

SINO:
    → Invocar SpecialistAgent (rol TestWriter/CodeFixer) con el gap report:
        Agent(SpecialistAgent,
              role="TestWriter" si COVERAGE_GAP | "CodeFixer" si TEST_FAILURE,
              context={gap_report, uncovered_lines, failing_tests},
              worktree=./worktrees/<tarea>)
    → SpecialistAgent: escribe tests o corrige código → commit en feature/<tarea>
    → Volver a Paso 2
```

### Paso 5 — Emitir LOOP_GREEN

```
LOOP_GREEN_REPORT:
  iterations_used: <n>
  tests_passed: <n>
  tests_failed: 0
  coverage_total_pct: <valor real>
  coverage_threshold_used: <valor de spec o default>
  coverage_per_module: {<módulo>: <pct>, ...}
  tool_output_sha256: <sha256 del output capturado>  ← trazabilidad de herramienta
```

Este reporte se inyecta como input al StandardsAgent en Gate 2b.
StandardsAgent no re-ejecuta pytest — consume el LOOP_GREEN_REPORT como fuente de verdad.

---

## Contrato con Gate 2b

**Precondición para invocar Gate 2b:**
Gate 2b (`contracts/gates.md §Gate 2b`) solo puede ser invocado cuando:
1. CI Loop emitió `LOOP_GREEN`, Y
2. El `LOOP_GREEN_REPORT` está disponible como input para StandardsAgent

**El StandardsAgent en Gate 2b:**
- Recibe el `LOOP_GREEN_REPORT` pre-generado
- No re-ejecuta pytest
- Valida: `tests_failed == 0` Y `coverage_total_pct >= umbral_threshold_used`
- Si el reporte no existe o no es GREEN → Gate 2b emite `BLOQUEADO_POR_HERRAMIENTA`
  (el gate no puede proceder sin datos de herramienta — no puede asumir cobertura)

---

## Límites del CI Loop

| Parámetro | Valor | Razón |
|---|---|---|
| `MAX_ITERATIONS` | 3 | Más de 3 ciclos indica problema sistémico — requiere revisión humana |
| Timeout por iteración | 300s | Scan + ejecución de tests razonable para proyectos medianos |
| Timeout total | `MAX_ITERATIONS × 300s` | El loop no puede bloquear indefinidamente |

**Si el timeout total se excede:** emitir `LOOP_TIMEOUT` → escalar al Master (mismo protocolo que LOOP_EXHAUSTED).

---

## Registro de Iteraciones (AuditAgent)

Cada iteración del loop se registra en `logs_veracidad/acciones_realizadas.txt`:

```
[TIMESTAMP] CI_LOOP_ITER: <n> — feature/<tarea>
[TIMESTAMP] ESTADO: TEST_FAILURE | COVERAGE_GAP | GREEN
[TIMESTAMP] COVERAGE: <pct>% (umbral: <umbral>%)
[TIMESTAMP] TESTS: <passed>/<total> — failed: <lista>
[TIMESTAMP] CORRECCIÓN: SpecialistAgent/<rol> — <n> archivos modificados
[TIMESTAMP] COMMIT: <sha_del_fix>
```

---

## Integración con el Framework Quality Gate (MODO_META)

En `MODO_META_ACTIVO` (objeto de trabajo es el framework), pytest-cov no aplica directamente
(los archivos son `.md`, no código Python). El CI Loop se adapta:

```
En MODO_META:
  Paso 2 equivalente → ejecutar grep checks del Framework Quality Gate (skills/framework-quality.md):
    • Cross-reference integrity   (grep de referencias cruzadas rotas)
    • No framework placeholders   (grep de [PENDIENTE] en archivos modificados)
    • Protocol integrity          (grep de estados/modos/agentes mencionados sin definir)
  Si cualquier check falla → estado = COVERAGE_GAP (tratamiento idéntico)
  LOOP_GREEN solo cuando todos los grep checks pasan con 0 resultados
```
