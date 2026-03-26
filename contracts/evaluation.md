# Contracts — Evaluation Rubric
> Define el sistema de scoring 0-1 para comparar outputs de Specialist Agents paralelos.
> Usado por EvaluationAgent. Fuente canónica de dimensiones, pesos y resource policy.
> Versión: 1.0 | Generado en: T1 del redesign PIV/OAC v3.2
>
> **Separación de esquemas:** este contrato define el rubric de scoring en tiempo real (EvaluationAgent, FASE 5b/5c). Para métricas DORA de sesión completa al cierre (AuditAgent, FASE 8), ver `metrics/sessions.md`. Los dos esquemas son independientes: no se mezclan ni se solapan.

---

## Dimensiones de Scoring

| Dimensión | Peso | Herramienta | Método |
|-----------|------|-------------|--------|
| FUNC — Completitud funcional | 0.35 | null | cobertura de ACs de specs/active/functional.md |
| SEC — Cumplimiento de seguridad | 0.25 | semgrep / bandit / grep | findings_ratio: (críticos / total_checks) invertido |
| QUAL — Calidad de código | 0.20 | pytest-cov + ruff | coverage_pct normalizado + violations_ratio invertido |
| COH — Coherencia arquitectural | 0.15 | null | LLM vs architecture.md — rubric estructurado |
| FOOT — Footprint mínimo | 0.05 | git diff --stat | files_changed / files_declared_in_plan |

**Notas:**
- Dimensiones con herramienta: resultado determinista de tool — no juicio LLM
- Dimensiones sin herramienta (FUNC, COH): LLM con rubric estructurado (no prosa libre)
- Score agregado: suma ponderada de las 5 dimensiones = valor en [0.0, 1.0]
- Si una herramienta no puede ejecutarse → score de esa dimensión = `BLOQUEADO_POR_HERRAMIENTA`, no 0.0

---

## Rubric por Dimensión

### FUNC — Completitud funcional (0.35)

```
Para cada AC en specs/active/functional.md del RF asignado a la tarea:
  - AC cubierto con código verificable: +1
  - AC parcialmente cubierto (lógica presente, falta caso edge): +0.5
  - AC ausente: +0

score_FUNC = (ACs_cubiertos + 0.5 * ACs_parciales) / ACs_totales
```

Notas:
- EvaluationAgent lee specs/active/functional.md para obtener los ACs del RF de la tarea
- La cobertura se evalúa mediante lectura del diff del experto (git show), no del código completo
- Si specs/active/functional.md no está disponible → BLOQUEADO_POR_HERRAMIENTA

### SEC — Cumplimiento de seguridad (0.25)

```
findings_criticos = semgrep/bandit reporta N hallazgos críticos o altos
total_checks = número de reglas ejecutadas

score_SEC = 1 - (findings_criticos / total_checks)
score_SEC se clampea a [0.0, 1.0]

Si findings_criticos > 0 → EvaluationAgent marca la dimensión con flag SEC_FINDINGS_PRESENT
El Domain Orchestrator recibe el flag junto al score — puede detener el torneo aunque el score sea >0
```

Notas:
- Herramienta preferida: semgrep (si disponible) → bandit (fallback) → grep de patrones básicos (último recurso)
- Herramienta usada debe quedar registrada en el campo "tool" del schema JSONL

### QUAL — Calidad de código (0.20)

```
score_cov  = pytest_coverage_pct / 100.0          # normalizado [0, 1]
violations = ruff_violations_count
max_violations_toleradas = 10                       # configurable en specs/active/quality.md si existe

score_ruff = max(0.0, 1.0 - (violations / max_violations_toleradas))
score_QUAL = 0.5 * score_cov + 0.5 * score_ruff
```

Notas:
- pytest-cov y ruff se ejecutan en el worktree del experto (no en el repo principal)
- Si pytest no puede ejecutarse → score_cov = BLOQUEADO_POR_HERRAMIENTA
- Si ruff no puede ejecutarse → score_ruff = BLOQUEADO_POR_HERRAMIENTA

### COH — Coherencia arquitectural (0.15)

```
EvaluationAgent lee specs/active/architecture.md y evalúa el diff del experto:

Criterios (rubric estructurado — respuesta binaria por ítem, no prosa):
  [ ] El experto implementa en la capa declarada en architecture.md
  [ ] No hay bypass de capas (Transport→Domain→Data)
  [ ] Las interfaces declaradas en el plan son las implementadas
  [ ] No hay dependencias externas no declaradas en architecture.md

score_COH = ítems_cumplidos / 4
```

### FOOT — Footprint mínimo (0.05)

```
files_changed   = git diff --stat feature/<tarea>/<experto> | contar archivos modificados
files_declared  = número de archivos declarados en el plan aprobado en Gate 2

score_FOOT = min(1.0, files_declared / files_changed)
  # Si files_changed == files_declared → score 1.0 (footprint exacto)
  # Si files_changed > files_declared → score < 1.0 (experto tocó más de lo necesario)
  # Si files_changed < files_declared → score 1.0 (experto fue más eficiente — no penalizar)
```

---

## Resource Policy

```
early_termination_threshold: 0.90
  # Si EvaluationAgent detecta que algún experto alcanza este score durante ejecución,
  # emite RECOMENDACIÓN DE TERMINACIÓN TEMPRANA al Domain Orchestrator.
  # El Domain Orchestrator tiene autoridad exclusiva para ejecutar la terminación.
  # EvaluationAgent NUNCA ejecuta terminación autónomamente.
  # La recomendación es solo eso — una recomendación, no una instrucción.

max_tokens_per_expert:
  nivel_1: 8000
  nivel_2_simple: 20000    # ≤3 archivos, sin dependencias complejas
  nivel_2_complex: 50000   # arquitectura nueva, múltiples dependencias

min_experts_to_compare: 2
  # No hay torneo con 1 solo experto.
  # early_termination solo aplica si hay ≥2 expertos activos en la tarea.
  # Con 1 experto, EvaluationAgent solo produce el score final (no recomendación de terminación).

early_termination_preserve_branches: true
  # Las ramas de expertos terminados prematuramente se preservan para auditoría post-Gate 3.
  # No se eliminan worktrees hasta que AuditAgent confirme cierre de FASE 8.
```

---

## Schema JSONL para logs_scores/

Cada registro es append-only en `logs_scores/<session_id>.jsonl`.

```json
{
  "schema_version": "1.0",
  "objective_id": "<string — join con .piv/active/>",
  "task_id": "<string — identifica la tarea del DAG>",
  "expert_id": "<string — nombre del Specialist Agent + rama>",
  "timestamp_iso8601": "<ISO 8601 con timezone>",
  "scores_per_criterion": {
    "FUNC": {
      "score": 0.0,
      "tool": null,
      "acs_covered": 0,
      "acs_total": 0
    },
    "SEC": {
      "score": 0.0,
      "tool": "semgrep",
      "findings": 0,
      "checks": 0,
      "sec_findings_present": false
    },
    "QUAL": {
      "score": 0.0,
      "tool": "pytest-cov+ruff",
      "coverage": 0.0,
      "violations": 0
    },
    "COH": {
      "score": 0.0,
      "tool": null,
      "rationale": ""
    },
    "FOOT": {
      "score": 0.0,
      "tool": "git diff --stat",
      "files_changed": 0,
      "files_declared": 0
    }
  },
  "total_score": 0.0,
  "winner": false,
  "early_terminated": false,
  "evaluator_agent": "<string>",
  "rubric_version": "<versión de contracts/evaluation.md usada>",
  "tokens_consumed": 0
}
```

**Reglas del schema:**
- `winner: true` solo para el experto seleccionado al cierre del torneo — exactamente 1 por tarea
- `early_terminated: true` si el experto fue detenido antes de completar por recomendación aceptada
- `total_score` debe coincidir con la suma ponderada de `scores_per_criterion`
- Si una dimensión es `BLOQUEADO_POR_HERRAMIENTA` → registrar como string en el campo `score` de esa dimensión (no float 0.0) para distinguirlo de un score real

---

## Integridad de logs_scores/

Al cierre de cada sesión, AuditAgent calcula el SHA-256 del archivo `logs_scores/<session_id>.jsonl` y lo registra en `engram/audit/gate_decisions.md`. Mecanismo idéntico al de `logs_veracidad/` (ver `registry/audit_agent.md §3. Protocolo de Escritura Append-Only`).

El archivo `logs_scores/` es append-only: ningún agente puede modificar registros previos. Si un cálculo estuvo incorrecto → agregar un registro nuevo con `correction_of: "<timestamp del registro original>"` y el valor correcto.

---

## Restricciones del EvaluationAgent

1. Solo puede leer subramas mediante `git show feature/<tarea>/<experto>:<path>` — nunca mediante `git checkout`
2. No puede escribir en ningún worktree de experto
3. No emite veredicto de Gate 1 — esa autoridad es exclusiva de CoherenceAgent
4. No ejecuta terminación temprana autónomamente — solo emite recomendación al Domain Orchestrator
5. No puede acceder a `engram/security/` (acceso exclusivo de SecurityAgent)

---

## Registro de Versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-03-22 | Creación inicial — dimensiones, pesos, resource policy, schema JSONL |
