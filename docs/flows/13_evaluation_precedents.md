# Flow 13 — Evaluation & Precedents System

> Parte del redesign PIV/OAC v3.3 (evaluation layer).
> Describe el ciclo completo: scoring paralelo → torneo → precedente.
> Fuente: `contracts/evaluation.md`, `registry/evaluation_agent.md`, `contracts/gates.md §Gate 1`

## Contexto

- EvaluationAgent activo desde FASE 5
- CoherenceAgent mantiene autoridad exclusiva de Gate 1
- Precedentes: solo post-Gate 3 en estado VALIDADO

## Flujo Completo

```mermaid
flowchart TD
    START([FASE 4: Gate pre-código aprobado]) --> FASE5_START

    subgraph FASE5_START["FASE 5 — Expertos en paralelo + EvaluationAgent (FASE 5b)"]
        direction LR
        EA_LAUNCH["[paralelo] EvaluationAgent lanzado con run_in_background=True"]
        SA_LAUNCH["[paralelo] Specialist Agents en worktrees aislados"]
        EA_LAUNCH & SA_LAUNCH --> SCORING
    end

    subgraph SCORING["FASE 5b — Scoring por checkpoints (EvaluationAgent)"]
        SC1["git show read-only → acceso a outputs de expertos\n(nunca git checkout de ramas activas)"]
        SC1 --> SC2["Score por dimensión:\nFUNC (0.35) / SEC (0.25) / QUAL (0.20) / COH (0.15) / FOOT (0.05)\nRubric: contracts/evaluation.md"]
        SC2 --> SC3["Checkpoint scores → logs_scores/<session_id>.jsonl\n(append-only)"]
        SC3 --> EARLY_TERM_CHECK{¿Score ≥ 0.90\ny ≥2 expertos activos?}
        EARLY_TERM_CHECK -->|SÍ| EARLY_REC["RECOMENDACIÓN DE TERMINACIÓN\nEmitida al Domain Orchestrator\n(no ejecuta autónomamente)"]
        EARLY_TERM_CHECK -->|NO| CONTINUE_SCORING["Continuar scoring\nhasta completado"]
        EARLY_REC --> DO_DECIDE{Domain Orchestrator\ndecide}
        DO_DECIDE -->|Acepta| EARLY_STOP["Detener experto(s)\nno ganadores\nearly_terminated: true\nen logs_scores/"]
        DO_DECIDE -->|Rechaza| CONTINUE_SCORING
        EARLY_STOP --> FASE5C
        CONTINUE_SCORING --> WAIT_ALL["Esperar completado\nde todos los expertos"]
        WAIT_ALL --> FASE5C
    end

    subgraph FASE5C["FASE 5c — Comparación y Selección"]
        F5C1["EvaluationAgent produce ranking final de scores"]
        F5C1 --> F5C2["Domain Orchestrator selecciona approach ganador\n(winner: true en logs_scores/)"]
        F5C2 --> F5C3["Scores registrados en logs_scores/\n(ganadores + perdedores, todos con winner flag)"]
        F5C3 --> F5C4["Scores enviados a CoherenceAgent\ncomo insumo para Gate 1"]
    end

    subgraph GATE1["GATE 1 — CoherenceAgent (autoridad exclusiva)"]
        G1A["Recibe:\n• Análisis de diffs entre subramas\n• Scores de EvaluationAgent (insumo informativo)"]
        G1A --> G1B["Decide: merge de expertos según coherencia arquitectural\n(checklist canónico: contracts/gates.md §Gate 1)"]
        G1B --> G1C["EvaluationAgent NO vota en Gate 1\nSolo provee datos — veredicto es exclusivo de CoherenceAgent"]
    end

    subgraph GATE2["GATE 2 — Security + Audit + Standards"]
        G2["Revisión de código en feature/<tarea>\nAprobación → merge feature/<tarea> → staging"]
    end

    subgraph GATE3["GATE 3 — staging → main (confirmación humana)"]
        G3["Security + Audit + Standards aprueban staging integral\nMaster presenta al usuario\n(confirmación válida requerida: contracts/gates.md §Gate 3)"]
    end

    subgraph FASE8B["FASE 8b — Registro de Precedente (post-Gate 3)"]
        P1["AuditAgent (delegación a EvaluationAgent, profundidad 1)"]
        P1 --> P2["Escribe: engram/precedents/<id>.md\nestado inicial: REGISTRADO"]
        P2 --> P3["Actualiza: engram/precedents/INDEX.md"]
        P3 --> P4["Gate 3 confirmado → estado: VALIDADO"]
        P4 --> P5["SHA-256 en engram/audit/gate_decisions.md"]
    end

    FASE5_START --> SCORING
    FASE5C --> GATE1
    GATE1 --> GATE2
    GATE2 --> GATE3
    GATE3 --> FASE8B
    FASE8B --> END([Precedente VALIDADO disponible para sesiones futuras])
```

## Uso en Sesiones Futuras

```mermaid
flowchart TD
    NEW_SESSION([FASE 1 — nueva sesión: Master Orchestrator]) --> READ_IDX
    READ_IDX["Lee engram/precedents/INDEX.md"]
    READ_IDX --> FILTER["Filtra por task_type relevante\n(DEV / RES / META)"]
    FILTER --> PREC_CHECK{¿Existe precedente VALIDADO\ncon score ≥ 0.85?}
    PREC_CHECK -->|SÍ| LOAD_PREC["Carga como estrategia de partida\npara Domain Orchestrator\n(incluye: approach ganador, scores, herramientas usadas)"]
    PREC_CHECK -->|NO| BUILD_FROM_SCRATCH["Construir DAG desde cero\nsegún specs/active/"]
    LOAD_PREC --> CONTINUE([Continuar con FASE 2])
    BUILD_FROM_SCRATCH --> CONTINUE
```

## Archivos de Referencia

| Archivo | Rol |
|---------|-----|
| `contracts/evaluation.md` | Rubric de scoring — 5 dimensiones, pesos, schema JSONL |
| `contracts/parallel_safety.md` | Protocolo de aislamiento y early termination |
| `contracts/gates.md §Gate 1` | CoherenceAgent como única autoridad de Gate 1 |
| `registry/evaluation_agent.md` | Protocolo completo del agente |
| `registry/coherence_agent.md` | Consumidor de scores — Gate 1 |
| `registry/audit_agent.md` | Escritor principal de `engram/precedents/` |
| `engram/precedents/INDEX.md` | Destino de precedentes validados |
| `logs_scores/` | Registros JSONL de scoring (append-only) |
