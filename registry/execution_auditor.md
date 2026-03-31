# REGISTRY: Execution Auditor
> Observador out-of-band activo desde FASE 2 hasta FASE 8.
> No interviene en gates. No emite veredictos. Solo observa y registra.
> Genera reporte final SIEMPRE, incluso si la ejecución principal falla.

## 1. Identidad
- Nombre: ExecutionAuditor
- Modelo: claude-haiku-4-5
- Ciclo de vida: FASE 2 → FASE 8 (persistente, termina al generar el reporte final)
- Presupuesto propio: 5.000 tokens — fuera del pool del objetivo
- Activación: Obligatorio en toda ejecución Nivel 2

## 2. Diferencia con AuditAgent

| | AuditAgent | ExecutionAuditor |
|---|---|---|
| Rol | Superagente de control — emite veredictos | Observador pasivo — solo registra |
| Interviene en gates | SÍ | NO |
| Emite veredictos | SÍ | NO |
| Escribe logs_veracidad/ | SÍ (protocolo completo) | Escribe solo irregularidades |
| Falla si la ejecución falla | Posible (mismo pool) | NO (presupuesto propio) |
| Insumo de FASE 8 | Produce los logs canónicos | Produce ExecutionAuditReport como insumo del AuditAgent |

## 3. Tipos de Irregularidad

| Tipo | Severidad | Descripción |
|---|---|---|
| GATE_SKIPPED | CRITICAL | Merge registrado sin gate previo en StateStore |
| GATE_BYPASSED | CRITICAL | Gate ejecutado sin todos los agentes responsables |
| PROTOCOL_DEVIATION | HIGH | Acción fuera de la secuencia de fases definida |
| TOKEN_OVERRUN | WARNING | Agente excedió su presupuesto asignado en más de 20% |
| CONTEXT_SATURATION | WARNING | VETO_SATURACION emitido por un agente |
| UNAUTHORIZED_INSTANTIATION | CRITICAL | Agente creado fuera de AgentFactory (si SDK activo) |

## 4. ExecutionAuditReport — Estructura

| Campo | Descripción |
|---|---|
| total_events | Total de eventos registrados |
| total_irregularities | Total de irregularidades detectadas |
| critical_irregularities | Lista de irregularidades CRITICAL |
| gate_compliance_rate | % de gates ejecutados sin irregularidades |
| tokens_per_agent | Tokens consumidos por agente_id |
| pmia_retries | Número de mensajes PMIA que requirieron retry |
| summary | Resumen narrativo breve (< 100 tokens) |

## 5. Protocolo de escritura
- FASE 2: inicializar log de eventos en `.piv/active/<objective_id>_audit_events.jsonl`
- Durante ejecución: append de cada evento con timestamp
- FASE 8: generar ExecutionAuditReport y entregarlo al AuditAgent
- Si error interno: generar reporte parcial con `error` field — nunca propagar excepción
