# Contracts — Parallel Safety
> Define las reglas de aislamiento para Specialist Agents que trabajan en paralelo.
> Todo agente que opere en un grupo paralelo debe cumplir este contrato.
> Verificable por CoherenceAgent durante monitorización de FASE 5.
> Versión: 1.0 | Generado en: T1 del redesign PIV/OAC v3.2

---

## Reglas de Aislamiento por Tipo de Agente

### Specialist Agent (experto en worktree)

**PUEDE LEER:**
- Su propio worktree: `worktrees/<tarea>/<experto>/` (acceso completo)
- `specs/active/` — solo lectura, nunca escritura durante ejecución activa
- Skills relevantes a su tarea (lazy loading — solo lo necesario)
- Su sección del `engram/INDEX.md`

**NO PUEDE:**
- Leer el worktree de otro Specialist Agent activo
- Escribir en `specs/active/` durante ejecución activa
- Acceder a `engram/security/` (acceso exclusivo de SecurityAgent)
- Ejecutar `git checkout` de otra rama que no sea la suya
- Modificar `/skills/` durante ejecución (Skills Inmutables)
- Acceder a `security_vault.md` sin instrucción humana explícita en el turno actual (Zero-Trust)

### EvaluationAgent

**PUEDE LEER (solo mediante git show):**
- `git show feature/<tarea>/<experto>:<path>` — lectura puntual read-only
- `git diff feature/<tarea>/exp_A..feature/<tarea>/exp_B` — comparación entre ramas
- `contracts/evaluation.md` — rubric de scoring
- `specs/active/functional.md` — ACs para evaluar la dimensión FUNC

**NO PUEDE:**
- `git checkout` de ninguna rama de experto (contamina el worktree activo)
- Escribir en ningún worktree de experto
- Emitir veredicto de Gate 1 (autoridad exclusiva de CoherenceAgent)
- Ejecutar terminación temprana autónomamente — solo emite RECOMENDACIÓN al Domain Orchestrator
- Acceder a `engram/security/` (acceso exclusivo de SecurityAgent)

### CoherenceAgent

**PUEDE LEER:**
- Diffs entre subramas activas (trabajar exclusivamente con diffs, nunca con código completo)
- `registry/coherence_agent.md` — su propio protocolo
- `engram/coherence/conflict_patterns.md` — patrones históricos

**NO PUEDE:**
- Resolver conflictos de seguridad unilateralmente — siempre escala al SecurityAgent
- Emitir veredicto sobre Gate 2 (feature/<tarea> → staging) — su veto cubre únicamente Gate 1
- Escalar directamente al usuario — siempre a través del Domain Orchestrator o Master Orchestrator
- Fragmentar en sub-agentes más allá de 2 niveles de profundidad desde el CoherenceAgent raíz

---

## Early Termination — Protocolo

La terminación temprana es una RECOMENDACIÓN del EvaluationAgent, no una acción autónoma.

### Paso 1 — Detección

EvaluationAgent detecta que Experto A alcanza `score ≥ early_termination_threshold` (0.90 por defecto, ver `contracts/evaluation.md`) durante evaluación intermedia.

### Paso 2 — Emisión de recomendación

EvaluationAgent emite `EVAL_EARLY_TERMINATION_RECOMMENDATION` al Domain Orchestrator:

```
EVAL_EARLY_TERMINATION_RECOMMENDATION:
  expert_winner: <id>
  score: <float>
  reason: "score ≥ threshold en evaluación intermedia"
  experts_to_terminate: [<id>, <id>]
  preserve_branches: true
```

### Paso 3 — Decisión del Domain Orchestrator

El Domain Orchestrator evalúa la recomendación y decide:

- **Si acepta:** notifica a los expertos → preserva sus ramas → procede con el ganador al Gate 1
- **Si rechaza:** continúa la ejecución paralela hasta completar de forma natural

La decisión del Domain Orchestrator es **final e irrevocable** en ese ciclo de evaluación. EvaluationAgent no puede insistir ni reenviar la misma recomendación en el mismo ciclo.

### Paso 4 — Preservación de ramas terminadas anticipadamente

- Las ramas `feature/<tarea>/<experto_terminado>` se preservan hasta cierre de FASE 8
- AuditAgent las incluye en `uso_contexto.txt` como `TERMINADO_ANTICIPADAMENTE`
- No se eliminan worktrees hasta confirmación de AuditAgent en FASE 8

---

## Estado de Worktrees Terminados Anticipadamente

```
Estado en logs_veracidad/acciones_realizadas.txt:
[TIMESTAMP] ACCIÓN: WORKTREE_TERMINADO_ANTICIPADAMENTE
[TIMESTAMP] AGENTE: <experto_id>
[TIMESTAMP] RAMA: feature/<tarea>/<experto>
[TIMESTAMP] RAZÓN: EARLY_TERMINATION_RECOMENDADA_Y_ACEPTADA
[TIMESTAMP] SCORE_FINAL: <float>
[TIMESTAMP] PRESERVADA: true
```

```
Estado en logs_scores/<session_id>.jsonl:
{
  ...
  "early_terminated": true,
  "winner": false,
  ...
}
```

---

## Protocolo de Detección de Violaciones

CoherenceAgent verifica en cada checkpoint de FASE 5:

```
[ ] Ningún Specialist Agent ha hecho git checkout de rama ajena
[ ] EvaluationAgent no ha escrito en worktrees de expertos
[ ] Ningún Specialist Agent ha modificado specs/active/ durante ejecución activa
[ ] Ningún agente ha accedido a engram/security/ sin ser SecurityAgent
```

**Violación detectada:**
1. CoherenceAgent emite `ISOLATION_VIOLATION` al Domain Orchestrator con descripción específica
2. Domain Orchestrator pausa al agente infractor
3. Domain Orchestrator notifica al Master Orchestrator
4. Master Orchestrator determina si el trabajo del agente infractor es recuperable o debe descartarse

```
ISOLATION_VIOLATION:
  agente_infractor: <id>
  tipo: CHECKOUT_RAMA_AJENA | ESCRITURA_EN_WORKTREE_AJENO | MODIFICACION_SPECS | ACCESO_ENGRAM_SECURITY
  evidencia: <descripción específica>
  timestamp: <ISO8601>
  acción: Domain Orchestrator pausa al agente y notifica al Master
```

---

## Reglas de Paralelismo por Fase

### FASE 2 — Creación del Entorno de Control
Todos los agentes del entorno de control se lanzan en PARALELO REAL en el mismo mensaje:
- `Agent(SecurityAgent, run_in_background=True)`
- `Agent(AuditAgent, run_in_background=True)`
- `Agent(StandardsAgent, run_in_background=True)`
- `Agent(CoherenceAgent, run_in_background=True)`
- `Agent(ComplianceAgent, run_in_background=True)` — solo si compliance_scope != "NONE"

Esperar notificaciones de completado de TODOS antes de continuar a FASE 3.

### FASE 4 — Gate de Plan (por tarea)
Los gates de plan se lanzan en PARALELO REAL en el mismo mensaje:
- `Agent(SecurityAgent.review_plan, run_in_background=True)`
- `Agent(AuditAgent.review_plan, run_in_background=True)`
- `Agent(CoherenceAgent.review_plan, run_in_background=True)`

Esperar los tres. Todos deben aprobar. Ningún worktree existe hasta aprobación de los tres.

### FASE 5 — Ejecución de Expertos
Expertos de la misma tarea sin dependencias entre sí → PARALELO REAL:
- `Agent(SpecialistAgent_1, worktree=..., run_in_background=True)`
- `Agent(SpecialistAgent_2, worktree=..., run_in_background=True)`

Expertos de distintas tareas con dependencias → secuencial según el DAG.

CoherenceAgent monitoriza diffs en background durante toda la FASE 5:
- `Agent(CoherenceAgent.monitor_diff, run_in_background=True)` — por cada par de expertos activos

### FASE 6 — Merges (dos niveles)
- Gate 1 (CoherenceAgent): espera completado de CoherenceAgent → Domain Orchestrator ejecuta merge subramas → `feature/<tarea>`
- Gate 2b (Security + Audit + Standards): espera completado de los tres → Domain Orchestrator ejecuta merge `feature/<tarea>` → `staging`

**Regla "Esperar Gate antes de actuar":** Ningún merge, commit de integración ni acción irreversible se ejecuta antes de recibir el veredicto explícito de todos los agentes del gate activo.

---

## Garantías de Aislamiento

El cumplimiento de este contrato garantiza:

1. **Determinismo:** dos expertos que trabajan en paralelo sobre la misma base producen resultados comparables y auditables
2. **No contaminación:** ningún experto puede leer el trabajo de otro antes de Gate 1, evitando convergencia artificial
3. **Recuperabilidad:** cualquier violación de aislamiento es detectable por CoherenceAgent y reportable antes de que cause daño irreparable
4. **Trazabilidad:** cada decisión de terminación temprana queda registrada con su justificación en `logs_scores/` y `acciones_realizadas.txt`

---

## Registro de Versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-03-22 | Creación inicial — reglas de aislamiento, early termination, detección de violaciones |
| 1.1 | 2026-03-23 | C-04: Gate 2b incluye StandardsAgent (Security + Audit + Standards) en FASE 6 |
