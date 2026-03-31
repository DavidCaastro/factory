# Skill: Cost Control y Rate Limiting

## Propósito
Protocolo para controlar el consumo de tokens y costo USD en objetivos multi-agente.
Previene explosiones de costo en ejecuciones paralelas de agentes Opus.

## Presupuesto por Objetivo

Todo objetivo Nivel 2 define un `budget` antes de la ejecución:

```yaml
# En specs/active/INDEX.md — sección budget (obligatoria para Nivel 2)
budget:
  max_tokens_total: 500000          # Hard stop — MasterOrchestrator veta si se supera
  max_tokens_per_agent: 80000       # Por invocación de agente individual
  max_usd_estimated: 15.00          # Estimación a precio lista Anthropic
  alert_threshold_pct: 80           # VETO_SATURACIÓN se activa al 80%
  model_overrides:                  # Permite degradar modelo si el presupuesto se agota
    on_budget_80pct: downgrade_opus_to_sonnet
    on_budget_95pct: downgrade_sonnet_to_haiku
```

## Throttling por Tipo de Agente

| Tipo de agente | Max tokens/llamada | Max llamadas/objetivo | Modelo permitido |
|---|---|---|---|
| MasterOrchestrator | 8 000 | 3 | Opus |
| SecurityAgent | 6 000 | 5 | Opus |
| AuditAgent | 5 000 | 10 | Sonnet |
| CoherenceAgent | 4 000 | 15 | Sonnet |
| DomainOrchestrator | 6 000 | 5 por DO | Sonnet |
| SpecialistAgent | 12 000 | ilimitado | Haiku / Sonnet |

Cualquier agente puede solicitar escalado de modelo si detecta que su tarea supera su capacidad — pero debe registrar la razón en el log de AuditAgent antes de ejecutar la llamada escalada.

## VETO_SATURACIÓN — Hard Stop

Activado automáticamente por el MasterOrchestrator cuando:
1. Tokens acumulados del objetivo ≥ 80% de `max_tokens_total`
2. Costo USD estimado ≥ 80% de `max_usd_estimated`

Acciones al activar VETO_SATURACIÓN:
```
1. Escribir checkpoint en .piv/active/<objetivo-id>.json (ver skills/session-continuity.md §3)
2. Notificar al usuario con estado actual del DAG (tareas completadas / pendientes)
3. Detener creación de nuevos agentes
4. Permitir finalización de agentes ya en ejecución (no kill abrupto)
5. Registrar en metrics/sessions.md: tokens_at_stop, usd_estimated_at_stop
```

## Estimación de Costo Previa

Antes de crear el entorno de control, el MasterOrchestrator estima el costo total:

```
costo_estimado = (
    n_tareas_dag × tokens_promedio_do × precio_sonnet +
    n_expertos × tokens_promedio_specialist × precio_haiku +
    n_gate_reviews × tokens_gate × precio_sonnet +
    agentes_control × tokens_control × precio_opus
)
```

Precios de referencia (actualizar en cada sprint si cambian):
- Opus input: $15/M tokens — output: $75/M tokens
- Sonnet input: $3/M tokens — output: $15/M tokens
- Haiku input: $0.25/M tokens — output: $1.25/M tokens

Si `costo_estimado > max_usd_estimated`, el MasterOrchestrator presenta la estimación al usuario y solicita ajuste de presupuesto o reducción de scope antes de proceder.

## Registro en Métricas

Al cerrar cada objetivo, AuditAgent extiende la entrada en `metrics/sessions.md` con:
```yaml
cost:
  tokens_input: 0
  tokens_output: 0
  usd_actual: 0.00
  model_distribution:
    opus_pct: 0
    sonnet_pct: 0
    haiku_pct: 0
  budget_headroom_pct: 0    # (1 - actual/max) * 100
```

---

## Token Caps v4.0 — Presupuesto por Nivel de Tarea

Los siguientes caps son absolutos. El LogisticsAgent no puede superarlos.
Derivan de la clasificación Nivel 1/2 de CLAUDE.md, no del SDK.

| Nivel de tarea | Cap de tokens | Cuándo aplica |
|---|---|---|
| Nivel 1 | 8.000 | Micro-tarea: ≤2 archivos, sin arquitectura nueva, RF documentado |
| Nivel 2 (≤ 3 archivos) | 40.000 | Tarea simple con pocos archivos afectados |
| Nivel 2 estándar | 100.000 | Tarea típica del framework |
| Nivel 2 (≥ 10 archivos) | 200.000 | Tarea compleja, múltiples módulos |

## TokenBudgetReport en la presentación del DAG

El Master Orchestrator incluye el TokenBudgetReport en la presentación al usuario:

```
Objetivo: [nombre]
DAG: [N] tareas en [secuencia/paralela]

Estimación de recursos:
  Total estimado: X tokens (~$Y USD)
  Tareas con fragmentación recomendada: [lista]
  Warnings de estimación anómala: [lista o "ninguno"]

¿Aprobar DAG con este presupuesto? [confirmación humana]
```

## Señales de alerta v4.0

**WARNING_ANOMALOUS_ESTIMATE:** Si LogisticsAgent estima más tokens de los que
el cap permite, registra el warning en el TokenBudgetReport. El Master lo presenta
al usuario. No bloquea la ejecución — es una advertencia de scope.

**RealtimeMetrics alertas:**
- 75% del presupuesto configurado → WARNING al MasterOrchestrator
- 90% del presupuesto → CRITICAL → presentar al usuario antes de continuar

**Presupuestos independientes (no consumen del pool del objetivo):**
- LogisticsAgent: 3.000 tokens propios
- ExecutionAuditor: 5.000 tokens propios
