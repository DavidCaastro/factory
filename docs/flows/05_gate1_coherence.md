# Flujo 05 — Gate 1: Coherencia (merge subramas → rama de tarea)
> Proceso: CoherenceAgent autoriza el merge de subramas de expertos a la rama de tarea.
> Fuente: `registry/coherence_agent.md` §4–7, `registry/domain_orchestrator.md` §3
> Checklist canónico y condiciones de aprobación: `contracts/gates.md §Gate 1`

```mermaid
flowchart TD
    START([Todos los expertos de la tarea completados]) --> DIFF_REVIEW

    subgraph DIFF_REVIEW["Revisión final de diffs combinados"]
        DR1["Por cada par de subramas (A, B):"]
        DR1 --> DR2["1. Obtener diff A desde punto de ramificación\n2. Obtener diff B desde punto de ramificación\n3. Intersectar archivos modificados"]
        DR2 --> DR3{¿Intersección\nnon-vacía?}
        DR3 -->|NO| OK_PAIR[Este par: OK]
        DR3 -->|SÍ| COMPARE["Comparar semánticamente\ncambios en archivos comunes"]
        COMPARE --> DR4{¿Compatibles?}
        DR4 -->|SÍ| OK_PAIR
        DR4 -->|NO| CLASSIFY
    end

    subgraph CLASSIFY["Clasificación del Conflicto"]
        CL1{¿Tipo de conflicto?}
        CL1 -->|Afecta seguridad| SEC_ESC["SUSPENDER resolución\nEscalar al SecurityAgent:\n• Expertos en conflicto\n• Archivo(s)\n• Naturaleza\n• Versiones de cada experto\n• RF afectado\nSecurityAgent determina resolución\nCoherenceAgent aplica decisión"]
        CL1 -->|No bloquea integración\npero genera deuda| MENOR["CONFLICTO MENOR\nNotificar + proponer reconciliación\nCualquier experto puede aplicarla\nantes de reportar completado"]
        CL1 -->|Impediría merge limpio\no comportamiento incorrecto| MAYOR["CONFLICTO MAYOR\nPausar subramas afectadas"]
        CL1 -->|Invalida trabajo\no compromete RF| CRITICO["CONFLICTO CRÍTICO\nVeto inmediato\nEscalar a Master Orchestrator"]
    end

    subgraph MAYOR_FLOW["Resolución de Conflicto MAYOR"]
        MA1["CoherenceAgent reporta al Domain Orchestrator:\n• Expertos afectados\n• Archivo(s)\n• Impacto\n• Opciones A y B con trade-offs"]
        MA1 --> MA2{¿DO puede\nresolver?}
        MA2 -->|SÍ — elige opción A o B| MA3["DO aplica resolución\nRegistrar en acciones_realizadas.txt"]
        MA2 -->|NO — consecuencias fuera de dominio| MA4["DO reporta al Master con razón\nMaster presenta usuario:\nconflicto + opciones + impacto\nUsuario decide"]
        MA2 -->|DO no responde| MA5["CoherenceAgent escala\ndirectamente al Master\nMaster notifica usuario"]
        MA3 --> DIFF_REVIEW
        MA4 --> DIFF_REVIEW
        MA5 --> DIFF_REVIEW
    end

    subgraph CRITICO_FLOW["Resolución de Conflicto CRÍTICO"]
        CR1["Veto sobre merge de subramas\nReport:\n• Expertos afectados\n• Subramas vetadas\n• RF comprometido\n• Impacto en sistema"]
        CR1 --> CR2["Requiere: intervención del Master\no del usuario"]
    end

    subgraph GIT_CONFLICT["Conflictos Técnicos de Git (marcadores <<<<<<<)"]
        GC1["DO detecta conflicto técnico al mergear"]
        GC1 --> GC2["Notificar al CoherenceAgent con diff del conflicto"]
        GC2 --> GC3{Naturaleza}
        GC3 -->|"Técnico puro\n(ej: imports duplicados)"| GC4["CoherenceAgent propone resolución concreta\nDO aplica y hace commit de resolución"]
        GC3 -->|Semántico / decisiones incompatibles| GC5["Tratar como MAYOR o CRÍTICO\nNunca: git merge --strategy-option=theirs\nNunca: descartar cambios sin evaluación"]
    end

    OK_PAIR --> FINAL_CHECK

    subgraph FINAL_CHECK["Verificación final de Gate 1"]
        FC1{¿Todos los expertos completados\nY sin CONFLICT_DETECTED pendiente\nY diffs mutuamente compatibles?}
        FC1 -->|NO| PENDING[Resolver conflictos pendientes]
        FC1 -->|SÍ| GATE1_OK
    end

    subgraph GATE1_OK["GATE_1_APROBADO"]
        G1["Emitir:\nCOHERENCE MERGE AUTHORIZATION\nTarea: feature/<tarea>\nSubramas evaluadas: [lista]\nConflictos detectados: N | Resueltos: N | Pendientes: 0\nEstado final: COHERENTE\nAUTORIZADO para merge a feature/<tarea>: SÍ\n(ver contracts/gates.md §Gate 1 para checklist canónico)"]
        G1 --> G2["Domain Orchestrator ejecuta:\ngit merge feature/<tarea>/<experto-1> → feature/<tarea>\ngit merge feature/<tarea>/<experto-2> → feature/<tarea>"]
    end

    PENDING --> CLASSIFY
    SEC_ESC --> DIFF_REVIEW
    MENOR --> DIFF_REVIEW
    MAYOR --> MAYOR_FLOW
    CRITICO --> CRITICO_FLOW
    CRITICO_FLOW --> PENDING

    G2 --> GATE2([Continuar a Flujo 06 — Gate 2 Calidad])
```

## Nota: EvaluationAgent como insumo de Gate 1

EvaluationAgent provee scores 0-1 como insumo informativo para CoherenceAgent. Los scores cubren las dimensiones FUNC/SEC/QUAL/COH/FOOT definidas en `contracts/evaluation.md`.

CoherenceAgent integra los scores en su análisis de coherencia pero **mantiene autoridad exclusiva del veredicto de Gate 1**. EvaluationAgent no puede vetar ni aprobar Gate 1 — su rol es estrictamente informativo.

El flujo de entrega de scores es: `EvaluationAgent → Domain Orchestrator → CoherenceAgent` (scores adjuntos al llamado de Gate 1). Ver `registry/evaluation_agent.md §6` para el protocolo completo.
