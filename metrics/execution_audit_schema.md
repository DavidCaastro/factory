# Metrics — Execution Audit Report Schema

> Generado por: ExecutionAuditor al cierre de FASE 8
> Insumo para: AuditAgent (incluir en logs de cierre) + metrics/sessions.md
> Formato: JSON almacenado en .piv/active/<objective_id>_execution_audit.json

## Schema

```json
{
  "objective_id": "OBJ-NNN",
  "generated_at": "<ISO8601>",
  "generated_by": "ExecutionAuditor",
  "execution_result": "COMPLETADO | FALLIDO | VETADO",

  "summary": {
    "total_events": 0,
    "total_gates_executed": 0,
    "total_irregularities": 0,
    "critical_irregularities": 0,
    "gate_compliance_rate": 1.0,
    "pmia_messages_total": 0,
    "pmia_retries": 0,
    "pmia_retry_rate": 0.0
  },

  "gates": [
    {
      "gate_id": "gate_2_T01",
      "gate_type": "gate_2_plan | gate_1_coherence | gate_2b | gate_3",
      "task_id": "T-01",
      "agents_executed": ["SecurityAgent", "AuditAgent", "CoherenceAgent"],
      "verdict": "APROBADO",
      "iterations": 1,
      "irregularities": []
    }
  ],

  "tokens_per_agent": {
    "MasterOrchestrator": {"input": 0, "output": 0, "total": 0},
    "SecurityAgent": {"input": 0, "output": 0, "total": 0},
    "AuditAgent": {"input": 0, "output": 0, "total": 0}
  },

  "csp_metrics": {
    "gates_with_csp": 0,
    "avg_filter_pct": 0.0,
    "filter_pct_by_gate": {}
  },

  "irregularities": [
    {
      "type": "GATE_SKIPPED | PROTOCOL_DEVIATION | TOKEN_OVERRUN | ...",
      "severity": "CRITICAL | HIGH | WARNING",
      "agent": "<agent_id>",
      "description": "<descripción>",
      "timestamp": "<ISO8601>"
    }
  ],

  "error": null
}
```

## Integración con metrics/sessions.md

Al registrar la sesión en metrics/sessions.md, AuditAgent extrae de este schema:
- `summary.gate_compliance_rate` → Métricas de Gate
- `tokens_per_agent` → Métricas de Costo (tokens reales, no N/D)
- `summary.total_irregularities` → Incidencias
- `csp_metrics.avg_filter_pct` → Métricas de Contexto
