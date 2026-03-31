# Flujo 01 — FASE 0: Preflight + Recuperación de Sesión
> Proceso: Primer paso de toda tarea Nivel 2. Detecta sesiones previas y valida intención.
> Fuente: `registry/orchestrator.md` §Protocolo de Checkpoint, `skills/session-continuity.md` §4

```mermaid
flowchart TD
    START([Objetivo Nivel 2 recibido]) --> CHECK_PIV

    subgraph CHECK_PIV["FASE 0 — Verificar Continuidad"]
        C1[Listar .piv/active/ → buscar *.json]
        C1 --> C2{¿Existe JSON\ncon fase_actual < 8?}
        C2 -->|NO| NEW_SESSION[Continuar a FASE 1\nnuevo objetivo]
        C2 -->|SÍ| LOAD_JSON
    end

    subgraph LOAD_JSON["Carga y validación de sesión previa"]
        L1["[PRIMERO] Leer <objetivo-id>.json\n→ establecer estado canónico"]
        L1 --> L2{¿Existe _summary.md?}
        L2 -->|SÍ| L3["[SEGUNDO] Leer summary\ncomo contexto LLM complementario"]
        L2 -->|NO| L5
        L3 --> L4{Validación cruzada:\n¿divergencia?}
        L4 -->|"a) fase_actual difiere ≥1\nb) tarea en summary sin ID en JSON\nc) gate aprobado en summary pero NO en JSON\nd) timestamp summary < JSON en ≥5 min"| DIV["IGNORAR summary completo\nAdvertir al usuario\nUsar solo JSON"]
        L4 -->|Sin divergencia| L5[Usar JSON + summary validado]
        DIV --> L5
    end

    L5 --> PRESENT

    subgraph PRESENT["Presentar sesión al usuario"]
        P1["Mostrar:\n• objetivo_titulo\n• Fase actual\n• Estado de tareas\n• Pendiente inmediato (si summary válido)"]
        P1 --> P2{Decisión del usuario}
        P2 -->|"[R] Reanudar"| RESUME["Cargar fase_actual y estado de tareas\ndesde JSON\nSummary = solo ayuda contextual"]
        P2 -->|"[N] Nuevo"| NEW_ARC["Archivar JSON y summary en\n.piv/completed/\nnota: 'superado por nuevo objetivo'\nContinuar desde FASE 1"]
        P2 -->|"[A] Abandonar"| ABANDON["Mover JSON y summary a\n.piv/failed/ con nota\nContinuar protocolo normal"]
    end

    RESUME --> RESUME_PHASE[Saltar a la fase registrada en JSON]
    NEW_ARC --> NEW_SESSION
    ABANDON --> NEW_SESSION

    NEW_SESSION --> INTENT_CHECK

    subgraph INTENT_CHECK["Validación de Intención (Nivel 0)"]
        I1{¿Viola ética,\nseguridad o legalidad?}
        I1 -->|SÍ| VETO["VETO INMEDIATO\nEmitir rechazo explícito con razón\nRegistrar en logs_veracidad/intent_rejections.jsonl\n{timestamp, objective_sha256, reason_category, summary, agent, phase}"]
        VETO --> STOP([FIN — sin agentes, sin ejecución])
        I1 -->|NO| CHECK_ENV
    end

    subgraph CHECK_ENV["Verificación de Entorno"]
        E1[Ejecutar scripts/validate_env.py]
        E1 --> E2{¿Herramientas\ncríticas faltantes?}
        E2 -->|SÍ| E3["Advertir al usuario\n(informativo — no bloquear aquí)"]
        E2 -->|NO| FASE1
        E3 --> FASE1
    end

    FASE1([Continuar a FASE 1 — Master DAG])
    RESUME_PHASE --> FASE1
```
