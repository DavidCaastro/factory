# Skill: Protocolo de Mensaje Inter-Agente (PMIA)

## Propósito
Define cómo los agentes se comunican entre sí de forma estructurada, segura
y eficiente en tokens. Complementa al CSP (que controla lo que ENTRA al agente).
El PMIA controla lo que SALE de un agente hacia otro.

## 1. Principio de Diseño

Los agentes NO se pasan contexto completo entre sí.
Solo viajan: tipo de evento + campos mínimos estructurados + artifact_ref si aplica.

**Prohibido en mensajes inter-agente:**
- Chain of thought o razonamiento interno
- Contenido completo de artefactos (usar artifact_ref)
- Credenciales o valores sensibles
- Texto libre no estructurado

## 2. Tipos de Mensaje

### GATE_VERDICT
Emitido por agentes de control al completar su revisión de gate.
```json
{
  "type": "GATE_VERDICT",
  "gate": "gate_2 | gate_1 | gate_2b | gate_3",
  "verdict": "APROBADO | RECHAZADO | APROBADO_CON_CONDICIONES",
  "agent_id": "<id>",
  "task_id": "<id>",
  "issues": [
    {"id": "SEC-001", "severity": "CRITICAL | HIGH | MEDIUM", "description": "<max 50 tokens>"}
  ],
  "artifact_ref": "<sha256 del artefacto revisado>",
  "timestamp": "<ISO8601>",
  "signature": "<HMAC-SHA256>"
}
```

### ESCALATION
Emitido por cualquier agente cuando detecta algo fuera de su scope o capacidad.
```json
{
  "type": "ESCALATION",
  "from_agent": "<id>",
  "to": "MasterOrchestrator | DomainOrchestrator | Human",
  "reason_code": "PROTOCOL_DEVIATION | SECURITY_VIOLATION | SCOPE_EXCEEDED | MAX_REJECTIONS",
  "task_id": "<id>",
  "context_snapshot_ref": "<ref en StateStore>",
  "timestamp": "<ISO8601>",
  "signature": "<HMAC-SHA256>"
}
```

### CROSS_ALERT
Canal lateral entre agentes de control (único canal fuera de gates).
Solo SecurityAgent, AuditAgent, CoherenceAgent, StandardsAgent pueden emitirlo.
```json
{
  "type": "CROSS_ALERT",
  "from_agent": "<id>",
  "to_agent": "<id>",
  "alert_type": "SECURITY_FINDING | COHERENCE_ISSUE | RF_GAP | QUALITY_ISSUE",
  "artifact_ref": "<ref del hallazgo>",
  "fragment_hint": "<keywords para filtrar el artifact_ref — max 20 tokens>",
  "timestamp": "<ISO8601>",
  "signature": "<HMAC-SHA256>"
}
```

### CHECKPOINT_REQ
Emitido por Domain Orchestrator o Master cuando se requiere checkpoint preventivo.
```json
{
  "type": "CHECKPOINT_REQ",
  "phase": "FASE_2 | FASE_4 | FASE_6 | FASE_7",
  "objective_id": "<id>",
  "control_environment_state": {
    "security_agent": "APROBADO | EN_EJECUCION | PENDIENTE",
    "audit_agent": "APROBADO | EN_EJECUCION | PENDIENTE",
    "coherence_agent": "APROBADO | EN_EJECUCION | PENDIENTE",
    "standards_agent": "APROBADO | EN_EJECUCION | PENDIENTE"
  },
  "active_gates": ["<gate_id>"],
  "timestamp": "<ISO8601>",
  "signature": "<HMAC-SHA256>"
}
```

## 3. Límites y Restricciones

| Restricción | Valor |
|---|---|
| Máximo tokens por mensaje | 300 |
| Chain of thought en mensaje | PROHIBIDO |
| Artefactos en mensaje | Solo por artifact_ref |
| Firma HMAC | Obligatoria (CryptoValidator) |
| Canales laterales (CROSS_ALERT) | Solo entre agentes de control |

## 4. Retry Protocol

El receptor valida la estructura del mensaje antes de procesarlo.

```
Receptor recibe mensaje
  └── ¿Estructura válida y firma correcta?
        SÍ → procesar normalmente
        NO (MALFORMED_MESSAGE) →
          └── Retornar: {type: "MALFORMED_MESSAGE", error: "<descripción>", expected_schema: "<tipo>"}
                └── Emisor recibe MALFORMED_MESSAGE
                      └── Reformatear mensaje
                            └── Reenviar (intento 1)
                                  └── Si falla de nuevo → reenviar (intento 2)
                                        └── Si falla por 3ra vez →
                                              ESCALATE al Domain Orchestrator
                                              que coordina la comunicación
```

Máximo 2 reintentos. Después de 2 fallos → ESCALATION inmediata.
Esta regla aplica a MALFORMED_MESSAGE, no a MessageExpired (que tiene su propio retry en CryptoValidator).

## 5. Integración con CryptoValidator

Los mensajes PMIA usan el mismo CryptoValidator del framework:
- `MessageTampered` (firma inválida): no reintentar → SECURITY_VIOLATION inmediato
- `MessageExpired` (TTL vencido): reintento con re-firma (max 3, backoff 2s)
- `MALFORMED_MESSAGE` (estructura incorrecta): retry protocol de §4

## 6. Métricas PMIA

El ExecutionAuditor registra:
- `pmia_messages_total`: total de mensajes inter-agente
- `pmia_retries`: mensajes que requirieron retry (MALFORMED_MESSAGE)
- `pmia_escalations`: mensajes que escalaron por agotamiento de reintentos
- `pmia_retry_rate`: pmia_retries / pmia_messages_total × 100
