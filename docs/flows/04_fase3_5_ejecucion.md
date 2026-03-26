# Flujo 04 — FASES 3–5: Domain Orchestrators + Ejecución de Expertos
> Proceso: Creación de DOs, plan de tarea, gate pre-código, worktrees, expertos paralelos.
> Fuente: `registry/domain_orchestrator.md`, `registry/orchestrator.md` §Paso 4-5

```mermaid
flowchart TD
    START([FASE 2 completada — entorno de control activo]) --> DAG_SCAN

    subgraph DAG_SCAN["FASE 3 — Crear Domain Orchestrators"]
        DS1["Identificar dominios del DAG\nsin dependencias entre sí"]
        DS1 --> DS2["Lanzar en PARALELO REAL los DOs sin dependencias:\nAgent(DO_A, run_in_background=True)\nAgent(DO_B, run_in_background=True)"]
        DS2 --> DS3["DOs con dependencias → lanzar\ncuando sus dependencias completen"]
    end

    DS3 --> TASK_LOOP

    subgraph TASK_LOOP["FASE 4 — Por cada tarea del sub-DAG (Domain Orchestrator)"]
        TL1["Cargar skill relevante de /skills/\nDiseñar plan detallado por capas"]
        TL1 --> GATE_PRE
    end

    subgraph GATE_PRE["Gate pre-código — BLOQUEANTE (PARALELO REAL)"]
        GP1["Lanzar en el mismo mensaje:"]
        direction LR
        GP2["Agent(SecurityAgent.review_plan\nrun_in_background=True)"]
        GP3["Agent(AuditAgent.review_plan\nrun_in_background=True)"]
        GP4["Agent(CoherenceAgent.review_plan\nrun_in_background=True)"]
        GP1 --> GP2
        GP1 --> GP3
        GP1 --> GP4
    end

    GP2 & GP3 & GP4 --> GATE_RESULT

    subgraph GATE_RESULT["Veredicto del gate pre-código"]
        GR1{¿Los TRES aprobaron?}
        GR1 -->|NO — 1er rechazo| GR2["Devolver al DO con razón específica\nDO revisa plan → repetir gate"]
        GR1 -->|NO — 2do rechazo del mismo plan| GR3["Escalar al Master Orchestrator\nNotificar usuario con historial"]
        GR1 -->|NO — DO no puede producir plan| GR4{Tipo de bloqueo}
        GR1 -->|SÍ — todos aprueban| CREATE_WT
        GR4 -->|Spec insuficiente| BLOCK_DISENO["BLOQUEADA_POR_DISEÑO\nver Flujo 11"]
        GR4 -->|Conocimiento insuficiente| BLOCK_INV["INVESTIGACIÓN_REQUERIDA\nver Flujo 11"]
        GR2 --> TASK_LOOP
    end

    subgraph CREATE_WT["SOLO TRAS APROBACIÓN — Crear worktrees"]
        CW1["git worktree add ./worktrees/<tarea>/<experto>\n-b feature/<tarea>/<experto>"]
        CW1 --> CW2{¿≥2 expertos\nasignados?}
        CW2 -->|SÍ| CW3["Activar CoherenceAgent.monitor_diff\nAgent(CoherenceAgent.monitor_diff\nrun_in_background=True)\npor cada par de expertos"]
        CW2 -->|NO| CW4
        CW3 --> CW4
    end

    subgraph FASE5["FASE 5 — Ejecución paralela de expertos"]
        F5A["Lanzar en PARALELO REAL por experto:\nAgent(SpecialistAgent\nworktree=./worktrees/<tarea>/<experto>\nrun_in_background=True)"]
        F5A --> F5B["Cada experto trabaja con contexto mínimo\nen su subrama aislada"]
        F5B --> F5C["CoherenceAgent monitoriza diffs\nentre subramas activas"]
        F5C --> F5D{¿Conflicto\ndetectado?}
        F5D -->|SÍ| F5E["Clasificar: MENOR / MAYOR / CRÍTICO\nver Flujo 05 — Gate 1"]
        F5D -->|NO| F5F{¿Todos los expertos\ncompletos?}
        F5F -->|NO| F5C
        F5F -->|SÍ| GATE1
    end

    CREATE_WT --> FASE5

    GATE1([Continuar a Flujo 05 — Gate 1 Coherencia])
```

## FASE 5b — Scoring Paralelo (EvaluationAgent)

EvaluationAgent corre en paralelo real con los Specialist Agents desde el inicio de FASE 5.

Acceso: `git show` read-only (nunca `git checkout` de ramas de expertos)
Rubric: `contracts/evaluation.md` (5 dimensiones: FUNC/SEC/QUAL/COH/FOOT)

```
Por cada checkpoint intermedio:
  → Score parcial por experto → registrado en logs_scores/<session_id>.jsonl
  → Si score ≥ early_termination_threshold (0.90): RECOMENDACIÓN DE TERMINACIÓN al Domain Orchestrator
  → DO decide autónomamente si acepta o rechaza la recomendación
```

**Restricciones del EvaluationAgent:**
- Solo lee subramas mediante `git show feature/<tarea>/<experto>:<path>` — nunca `git checkout`
- No puede escribir en ningún worktree de experto
- No emite veredicto de Gate 1 — esa autoridad es exclusiva de CoherenceAgent
- No ejecuta terminación temprana autónomamente — solo emite recomendación al Domain Orchestrator

## FASE 5c — Comparación y Selección

Al completar todos los expertos (o tras early termination aceptada por el DO):

```
  → EvaluationAgent produce ranking final de scores
  → Domain Orchestrator selecciona approach ganador
  → Scores (ganadores + perdedores) registrados en logs_scores/ JSONL (append-only)
  → Scores pasan a CoherenceAgent como insumo para Gate 1
  → CoherenceAgent mantiene autoridad exclusiva del veredicto de Gate 1
```

**Nota:** Si hay un solo experto asignado a la tarea, EvaluationAgent produce el score final sin recomendación de terminación (no hay torneo con un solo participante). Ver `contracts/evaluation.md §Resource Policy`.
