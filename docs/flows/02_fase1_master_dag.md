# Flujo 02 — FASE 1: Master Orchestrator — Construcción del DAG
> Proceso: El Master Orchestrator lee specs, descompone el objetivo y presenta el grafo al usuario.
> Fuente: `registry/orchestrator.md` §Protocolo de Activación

```mermaid
flowchart TD
    START([FASE 0 completada — intención aprobada]) --> HIST

    subgraph HIST["Paso 1 — Contexto histórico y specs"]
        H1{¿Existe metrics/sessions.md?}
        H1 -->|SÍ| H2["Leer últimas 3 entradas\n→ detectar tendencias:\n• first-pass rate < 80% en 2+ sesiones → advertir\n• VETO_SATURACIÓN > 0 → reducir scope\n• Gates BLOQUEADO_POR_HERRAMIENTA > 0 → verificar entorno"]
        H1 -->|NO| H3
        H2 --> H3[Leer specs/active/INDEX.md\n→ validar compliance_scope + execution_mode]
        H3 --> H4{execution_mode?}
    end

    H4 -->|INIT| INIT_MODE["Activar protocolo INIT\nver skills/init.md\nEntrevista 7Q → genera specs/active/\nCambiar execution_mode al modo destino\nContinuar desde FASE 1 en modo destino"]
    H4 -->|DEVELOPMENT| DEV_READ["Leer functional.md + architecture.md"]
    H4 -->|RESEARCH| RES_READ["Leer research.md"]
    H4 -->|MIXED| MIX_READ["Leer functional.md + research.md + architecture.md\nCada tarea del DAG declara Modo: DEV | RES"]

    DEV_READ --> RF_CHECK
    RES_READ --> RF_CHECK
    MIX_READ --> RF_CHECK

    subgraph RF_CHECK["Validación de Requisitos"]
        R1{¿Existen RFs o RQs\ndocumentados para el objetivo?}
        R1 -->|NO| R_BLOCK["BLOQUEADO\nDevolver al usuario:\nspec no tiene RF/RQ que respalde el objetivo"]
        R1 -->|SÍ| R2{¿Spec tiene información\nsuficiente para descomponer\nen tareas?}
        R2 -->|NO| R_ASK["Listar preguntas específicas al usuario\nNunca asumir ni inventar info"]
        R2 -->|SÍ| BUILD_DAG
    end

    subgraph BUILD_DAG["Paso 2 — Construcción del DAG"]
        D1["Identificar todas las tareas necesarias\nDeterminar: PARALELA vs SECUENCIAL\nDeterminar: cuántos expertos por tarea"]
        D1 --> D2["Producir tabla:\n| Tarea | Dominio | Tipo | Expertos | Depende de |"]
        D2 --> D3["Criterios de secuencialidad:\n• Output de A → input de B\n• Interfaz/contrato debe estar primero\n• Tarea valida resultado de otra"]
        D3 --> D4["Criterios para ≥2 expertos:\nver skills/orchestration.md\nPregunta 1: ¿Solo un enfoque técnico válido existe?\nPregunta 2: ¿El volumen justifica 1 experto?\nPregunta 3: ¿El riesgo de error es bajo?\n→ 3 SÍ: 1 experto | ≥2 NO: 2 expertos"]
    end

    subgraph COMPLIANCE_EVAL["Paso 3 — Evaluación de Compliance"]
        CL1["Evaluar implicaciones: GDPR, CCPA, HIPAA, etc."]
        CL1 --> CL2{¿Riesgo irresuelto\ncon código?}
        CL2 -->|SÍ| CL3["Generar borrador Documento de Mitigación\nComplianceAgent lo completará en FASE 2"]
        CL2 -->|NO| CL4[compliance normal]
    end

    subgraph CONTROL_TABLE["Paso 3b — Tabla de Activación Entorno de Control"]
        CT1["Leer compliance_scope de INDEX.md\nComparar fila a fila (no inferir):"]
        CT1 --> CT2["SecurityAgent   → SIEMPRE SÍ\nAuditAgent      → SIEMPRE SÍ\nStandardsAgent  → SIEMPRE SÍ\nCoherenceAgent  → SIEMPRE SÍ\nComplianceAgent → SÍ si scope == FULL o MINIMAL\n                  NO si scope == NONE\nValor no reconocido → BLOQUEADO"]
    end

    D4 --> COMPLIANCE_EVAL
    COMPLIANCE_EVAL --> CONTROL_TABLE
    CT2 --> LOGISTICS

    subgraph LOGISTICS["Paso 2b — LogisticsAgent: Análisis de Recursos (v4.0, solo Nivel 2)"]
        LG1["Agent(LogisticsAgent, model=haiku, budget_tokens=3000)\n→ LogisticsAgent.analyze_dag(dag, specs)\n→ Produce TokenBudgetReport"]
        LG1 --> LG2{¿fragmentation_required\nen alguna tarea?}
        LG2 -->|SÍ| LG3["Ajustar número de expertos\nrecomendado en el DAG"]
        LG2 -->|NO| LG4[DAG sin cambios]
        LG3 --> LG5{¿WARNING_ANOMALOUS\n_ESTIMATE?}
        LG4 --> LG5
        LG5 -->|SÍ| LG6["Marcar tarea en informe\npara revisión del usuario"]
        LG5 -->|NO| LG7[Informe sin warnings]
        LG6 --> PRESENT
        LG7 --> PRESENT
    end

    LOGISTICS --> PRESENT

    subgraph PRESENT["Presentar al usuario"]
        PR1["Mostrar:\n• Grafo de dependencias (DAG)\n• TokenBudgetReport (estimación total + por tarea)\n• Tareas con fragmentation_required=true (si aplica)\n• WARNING_ANOMALOUS_ESTIMATE (si aplica)\n• Entorno de control determinado\n• Resumen de compliance\n• Borrador de Mitigación si aplica"]
        PR1 --> PR2{¿Usuario confirma?}
        PR2 -->|NO / cambios| ADJUST[Ajustar DAG y volver a presentar]
        PR2 -->|SÍ| FASE2
    end

    ADJUST --> BUILD_DAG

    FASE2([Continuar a FASE 2 — Crear Entorno de Control])
```
