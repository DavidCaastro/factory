# Flujo 10 — Continuidad de Sesión: Regla del 60% + Recuperación en FASE 0
> Proceso: Escritura proactiva de estado antes de compresión + recuperación tras reinicio.
> Fuente: `skills/session-continuity.md`, `registry/orchestrator.md` §Protocolo de Checkpoint

```mermaid
flowchart TD
    START([Orquestador activo durante ejecución]) --> MONITOR

    subgraph MONITOR["Monitorización continua del umbral de contexto"]
        M1["En cada acción del orquestador,\nverificar triggers deterministas:"]
        M1 --> M2{¿Algún trigger\nactivo?}

        subgraph TRIGGERS["Triggers del 60% (cualquiera dispara)"]
            TA["TRIGGER a)\n≥ 15 archivos distintos leídos\ndesde el último summary en la fase actual"]
            TB["TRIGGER b)\n≥ 3 ciclos completos de gate\n(plan → revisión → aprobación/rechazo)\ndesde el último summary"]
            TC_T["TRIGGER c)\nLa próxima acción requiere\n≥ 3 archivos simultáneamente\nY total acumulado llegaría a ≥ 15"]
            TD["TRIGGER subjetivo\nOrquestador estima subjetivamente\nque supera el 60%"]
        end

        M2 -->|SÍ — cualquier trigger| WRITE_SUMMARY
        M2 -->|NO| CONTINUE[Continuar ejecución]
    end

    subgraph WRITE_SUMMARY["Escritura de Summary (antes de continuar)"]
        WS1["1. Completar la acción atómica en curso\n(no interrumpir a mitad de operación)"]
        WS1 --> WS2["2. Escribir/actualizar:\n<objetivo-id>_summary.md\n→ Estado del DAG por tarea\n→ Decisiones de arquitectura\n→ Pendiente inmediato\n→ Notas de recuperación\n→ Máximo 200 líneas"]
        WS2 --> WS3["3. Escribir/actualizar:\n<objetivo-id>.json\n→ fase_actual\n→ tareas[*].estado\n→ tareas[*].gate_N_aprobado\n→ timestamp_ultimo_checkpoint"]
        WS3 --> WS4["4. Registrar en Notas de Recuperación:\nqué estaba haciendo exactamente"]
        WS4 --> RESUME_EXEC[5. Reanudar la tarea]
    end

    WRITE_SUMMARY --> CONTINUE

    subgraph CHECKPOINTS["Triggers obligatorios adicionales (siempre, independiente del 60%)"]
        CP1["Los Domain Orchestrators reportan al Master → Master actualiza:\n• DAG confirmado por usuario\n• Entorno de control completo\n• Plan de tarea aprobado por gate\n• Cada experto completa\n• Gate 1 aprobado\n• Gate 2 aprobado\n• Merge a staging completado"]
    end

    subgraph VETO_80["Distinción: 60% vs 80%"]
        V1["60% → Completar acción atómica → Escribir summary → CONTINUAR"]
        V2["80% → Emitir VETO_SATURACIÓN\nEscalar al orquestador padre\nNO continuar\nViolación si continúa sin escalar"]
        V2 --> VCAS["Cascada: si el padre también está ≥80%\nel padre emite su propio VETO_SATURACIÓN\ny escala al siguiente nivel superior\nHasta que llega al Master Orchestrator:\n→ Master presenta opciones al usuario:\n  [F] Fragmentar tarea en subtareas más pequeñas\n  [P] Pausar y retomar en nueva sesión\n  [C] Continuar con riesgo asumido (no recomendado)"]
    end

    subgraph RECOVERY["Recuperación en FASE 0 (nuevo inicio de sesión)"]
        R1["Listar .piv/active/ → buscar *.json"]
        R1 --> R2{¿JSON con\nfase_actual < 8?}
        R2 -->|NO| R_NEW[Continuar desde FASE 1]
        R2 -->|SÍ| R3["[PRIMERO] Leer JSON → estado canónico"]
        R3 --> R4{¿Existe _summary.md?}
        R4 -->|SÍ| R5["[SEGUNDO] Leer summary\ncomo contexto LLM complementario"]
        R4 -->|NO| R6
        R5 --> XVAL
    end

    subgraph XVAL["Validación cruzada (Zero-Trust Metodológico)"]
        XV1{¿Divergencia?}
        XV2["a) fase_actual summary ≠ JSON en ≥1 fase\nb) Tarea en summary sin ID en JSON\nc) Gate aprobado en summary ≠ JSON\nd) timestamp summary < JSON en ≥5 min"]
        XV1 -->|"Cualquier divergencia"| XV3["IGNORAR summary completo\nAdvertir al usuario\nUsar solo JSON"]
        XV1 -->|Sin divergencia| XV4[Usar JSON + summary validado]
        XV2 --> XV1
        XV3 & XV4 --> R6
    end

    R6 --> R7["Presentar al usuario con datos del JSON:\n• objetivo_titulo\n• Fase actual\n• Estado de tareas\n• Pendiente inmediato (solo si summary válido)"]
    R7 --> R8{Decisión}
    R8 -->|"[R] Reanudar"| R_RESUME["Fase y estado se cargan del JSON\nSummary = solo ayuda contextual\nEl JSON governa las acciones"]
    R8 -->|"[N] Nuevo"| R_NEW
    R8 -->|"[A] Abandonar"| R_FAIL["Mover JSON + summary a .piv/failed/\nContinuar normal"]

    subgraph ARTEFACTOS["Artefactos en .piv/active/"]
        AR1["JSON → Fuente de verdad para lógica de recuperación\nMarkdown → Fuente de verdad para contexto del orquestador\nAmbos coexisten — ninguno reemplaza al otro\nCapa 3 RUNTIME — en .gitignore, no se versiona"]
    end
```
