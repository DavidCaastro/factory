# logs_veracidad/ — Protocolo de Registro

## Estructura de directorios

```
logs_veracidad/
├── _global/                    ← eventos del framework en sí (no de productos)
│   ├── framework_events.jsonl  ← bitácora de eventos del framework (intent rejections, cambios meta)
│   └── intent_rejections.jsonl ← rechazos de intención FASE 0 (movido de raíz)
│
└── <product-id>/               ← un directorio por producto/objetivo
    ├── acciones.jsonl          ← cronología de eventos por agente
    ├── uso_contexto.jsonl      ← tokens, archivos cargados, saturaciones
    └── verificacion_rf.jsonl   ← RFs verificados contra código entregado
```

## Formato JSONL

Cada línea es un objeto JSON independiente (JSON Lines). Append-only. Nunca sobreescribir.

### Schema base (todos los tipos)
```json
{
  "ts": "2026-03-31T14:22:10Z",
  "session": "OBJ-003",
  "agent": "SecurityAgent",
  "event": "<tipo de evento>",
  ...campos específicos del tipo
}
```

### Tipos de evento en acciones.jsonl

| event | Campos adicionales |
|---|---|
| `GATE_VERDICT` | gate, verdict, issues_count, duration_ms |
| `AGENT_INSTANTIATED` | agent_type, model, requester |
| `AGENT_COMPLETED` | agent_type, tokens_used, result |
| `SECURITY_VIOLATION` | violation_type, description, action_taken |
| `PROTOCOL_DEVIATION` | description, detected_by |
| `VETO_SATURACION` | agent_type, context_pct, action |
| `CHECKPOINT_WRITTEN` | phase, state_keys_count |
| `MERGE_EXECUTED` | from_branch, to_branch, authorized_by |

### Schema uso_contexto.jsonl

```json
{
  "ts": "...", "session": "...", "phase": "FASE_6",
  "agent": "SecurityAgent", "event": "CONTEXT_SNAPSHOT",
  "tokens_input": 1200, "tokens_output": 340,
  "files_loaded": ["contracts/gates.md", "skills/backend-security.md"],
  "context_window_pct": 12.5,
  "csp_filter_pct": 0.32
}
```

### Schema verificacion_rf.jsonl

```json
{
  "ts": "...", "session": "...", "agent": "AuditAgent",
  "event": "RF_VERIFIED",
  "rf_id": "RF-CSP-01",
  "evidence": "contracts/gates.md:§CSP",
  "verdict": "CUMPLIDO | INCUMPLIDO | PARCIAL"
}
```

## Protocolo de escritura

1. Escritura exclusiva: AuditAgent (+ ExecutionAuditor para irregularidades)
2. Modo: append-only — nunca sobreescribir líneas existentes
3. Si el directorio `<product-id>/` no existe: crearlo antes del primer write
4. El `<product-id>` es el `objective_id` del producto (ej: OBJ-003, axonum-v0.2.0)
5. Al cierre de FASE 8: AuditAgent registra SHA-256 del archivo en engram/audit/gate_decisions.md

## Automatización

`scripts/fase8_auto.py` genera automáticamente las entradas JSONL al cierre del objetivo,
leyendo el estado de `.piv/active/` y el git log. El AuditAgent solo aprueba el reporte
— no tiene que escribir las líneas manualmente.
