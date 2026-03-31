# Flujo 03 — FASE 2: Creación del Entorno de Control
> Proceso: Lanzar todos los superagentes en paralelo real antes de cualquier experto.
> Fuente: `CLAUDE.md` §Protocolo Nivel 2 FASE 2, `registry/orchestrator.md` §Paso 4

```mermaid
flowchart TD
    START([FASE 1 completada — DAG confirmado por usuario]) --> CREAR_RAMA

    subgraph CREAR_RAMA["Infraestructura base"]
        BR1{¿Existe rama staging?}
        BR1 -->|NO| BR2["git checkout -b staging main"]
        BR1 -->|SÍ| BR3[Usar staging existente]
        BR2 --> LAUNCH
        BR3 --> LAUNCH
    end

    subgraph LAUNCH["Lanzar superagentes en PARALELO REAL\n(mismo mensaje, run_in_background=True)"]
        direction LR
        SA["Agent(SecurityAgent\nmodel=opus\nrun_in_background=True)"]
        AA["Agent(AuditAgent\nmodel=sonnet\nrun_in_background=True)"]
        STA["Agent(StandardsAgent\nmodel=sonnet\nrun_in_background=True)"]
        CA["Agent(CoherenceAgent\nmodel=sonnet\nrun_in_background=True)"]
    end

    subgraph CONDITIONAL["Agentes condicionales (mismo mensaje si aplica)"]
        CMP{compliance_scope\n!= NONE?}
        CMP -->|SÍ| CMP_AGENT["Agent(ComplianceAgent\nmodel=sonnet\nrun_in_background=True)"]
        CMP -->|NO| CMP_SKIP[ComplianceAgent no se crea]
    end

    LAUNCH --> CONDITIONAL
    CONDITIONAL --> WAIT

    subgraph WAIT["Esperar completado de todos los lanzados"]
        W1["Recibir notificaciones de:\n• SecurityAgent: LISTO\n• AuditAgent: LISTO\n• StandardsAgent: LISTO\n• CoherenceAgent: LISTO\n• ComplianceAgent: LISTO (si aplica)"]
        W1 --> W2{¿Todos\nnotificaron?}
        W2 -->|NO — 1er o 2do intento| W3[Esperar notificaciones restantes]
        W2 -->|NO — 3er intento sin respuesta| W4["Escalar al usuario\n(agente no responde)"]
        W3 --> W2
        W2 -->|SÍ| CHECKPOINT
    end

    subgraph CHECKPOINT["Checkpoint post-FASE 2"]
        CP1["Escribir .piv/active/<objetivo-id>.json\nfase_actual: 2\nagentes_activos: [lista]\nEntorno de control: ACTIVO"]
    end

    CHECKPOINT --> FASE3

    subgraph MODO_META["Nota: MODO_META_ACTIVO"]
        MM1["Si el objeto de trabajo ES el framework\n(rama agent-configs o equivalente):\nMaster declara MODO_META_ACTIVO en FASE 1\nStandardsAgent carga skills/framework-quality.md\nen lugar de skills/standards.md para Gate 2\nTodas las demás reglas permanentes siguen vigentes"]
    end

    FASE3([Continuar a FASE 3 — Crear Domain Orchestrators])
```
