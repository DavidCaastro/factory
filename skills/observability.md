# Skill: Observability Protocol — PIV/OAC v3.2

**Gap:** G-02 — OpenTelemetry instrumentation for traces, metrics, and logs across all PIV/OAC pipelines
**Status:** Active
**Applies to:** All agents and orchestrators operating within a PIV/OAC pipeline
**Integrates with:** `skills/agent-contracts.md` (G-07), `skills/fault-recovery.md` (G-03), `skills/cost-control.md` (G-04)
**SDK module:** `sdk/piv_oac/telemetry/` (see §3)

---

## Motivation

Without structured observability, failures in multi-agent pipelines are opaque. A gate rejection, a token spike, or a cascading fault leaves no queryable trail. This document defines the canonical OpenTelemetry instrumentation strategy for PIV/OAC: which signals to emit, what attributes to carry, how to correlate them, and which dashboards and alerts are required for production operation.

---

## 1. Por qué OpenTelemetry

- **Estándar CNCF — vendor-neutral, sin lock-in.** El mismo SDK instrumenta el código una sola vez y el destino de los datos se decide en configuración, no en código.
- **Tres señales en un solo SDK.** Traces, metrics y logs comparten un modelo de datos unificado y context propagation nativo.
- **Compatible con cualquier backend.** Jaeger, Grafana Tempo, Grafana Loki, Datadog, Honeycomb, y cualquier receptor que implemente el protocolo OTLP son soportados sin cambios al código de instrumentación.
- **Graceful degradation.** La librería está diseñada para ser no-op cuando no hay collector disponible, lo que permite usarla en entornos locales sin infraestructura adicional.

---

## 2. Tres Señales Instrumentadas

### 2.1 Traces (Distributed Tracing)

Cada invocación de agente corresponde a un span. El nombre del span sigue el patrón:

```
piv_oac.agent.<agent_type>
```

Ejemplos: `piv_oac.agent.SpecialistAgent`, `piv_oac.agent.SecurityAgent`, `piv_oac.agent.AuditAgent`.

**Atributos obligatorios del span:**

| Atributo | Tipo | Descripción |
|---|---|---|
| `agent.type` | string | Tipo de agente según `skills/agent-contracts.md` §1 |
| `agent.model` | string | Modelo utilizado (e.g., `claude-opus-4`, `claude-sonnet-4-6`) |
| `objective.id` | string | Identificador único del objetivo en ejecución |
| `gate.name` | string | Nombre del gate activo, si aplica (omitir si no hay gate) |
| `tokens.input` | int | Tokens de entrada consumidos en la invocación |
| `tokens.output` | int | Tokens de salida generados en la invocación |

**Jerarquía de spans:**

El span del orquestador que invoca al agente es el **span padre**. El agente invocado crea su propio span hijo propagando el `trace_id` y el `span_id` del padre. Esto permite reconstruir el árbol completo de invocaciones de un objetivo.

**Errores en span:**

Cuando un agente emite `FAILURE_TYPE` (según `skills/fault-recovery.md` §8.1), el span debe marcarse con:

```python
span.set_status(StatusCode.ERROR, description=failure_type)
span.set_attribute("error.type", failure_type)
span.set_attribute("otel.status_code", "ERROR")
```

El valor de `error.type` es el valor exacto del campo `FAILURE_TYPE` tal como aparece en el contrato de salida del agente (e.g., `AGENT_TIMEOUT`, `MALFORMED_OUTPUT`, `GATE_DEADLOCK`).

---

### 2.2 Metrics (Contadores e Histogramas)

Todas las métricas usan el prefijo `piv_oac.`. Se exponen vía OTLP y pueden ser consultadas desde cualquier backend compatible (Prometheus, Grafana Mimir, Datadog, etc.).

| Métrica | Tipo | Labels | Descripción |
|---|---|---|---|
| `piv_oac.agent.invocations` | Counter | `agent_type`, `model`, `objective_id`, `result` | Total de invocaciones de agente. `result`: `success` \| `failure` |
| `piv_oac.agent.tokens` | Histogram | `agent_type`, `model`, `direction` | Tokens por invocación. `direction`: `input` \| `output` |
| `piv_oac.gate.duration_ms` | Histogram | `gate_name`, `result` | Duración de cada revisión de gate en ms. `result`: `approved` \| `rejected` |
| `piv_oac.objective.cost_usd` | Counter | `objective_id`, `model` | Costo USD acumulado por objetivo y modelo, según precios en `skills/cost-control.md` |
| `piv_oac.context.usage_pct` | Gauge | `agent_type` | Porcentaje de contexto utilizado por agente. Permite detectar `VETO_SATURACIÓN` antes de que se active (umbral: 80% per `skills/cost-control.md`) |

**Nota sobre `piv_oac.objective.cost_usd`:** los precios de referencia por modelo están definidos en `skills/cost-control.md` (Opus: $15/$75 M tokens input/output; Sonnet: $3/$15; Haiku: $0.25/$1.25). El cálculo debe actualizarse en cada sprint junto con esa tabla.

---

### 2.3 Logs (Structured)

Cada gate emite un log estructurado en formato JSON al momento de emitir su veredicto. El log debe incluir los campos de correlación OTel para poder cruzarlo con el trace correspondiente.

**Esquema de log de gate:**

```json
{
  "timestamp": "<ISO-8601>",
  "gate_name": "<nombre del gate>",
  "verdict": "APPROVED | REJECTED | CONDITIONAL_APPROVED",
  "agent_type": "<tipo de agente revisor>",
  "objective_id": "<id del objetivo>",
  "findings": "<lista de hallazgos separada por comas, o null si APPROVED>",
  "trace_id": "<OTel trace_id en formato hex-16-bytes>",
  "span_id": "<OTel span_id en formato hex-8-bytes>"
}
```

Los campos `trace_id` y `span_id` se obtienen del span activo en el momento de emitir el log:

```python
from opentelemetry import trace as otel_trace

span = otel_trace.get_current_span()
ctx = span.get_span_context()
trace_id = format(ctx.trace_id, "032x")
span_id = format(ctx.span_id, "016x")
```

Los logs de gate se correlacionan directamente con el campo `FINDINGS` del contrato de `SecurityAgent` y `AuditAgent` definidos en `skills/agent-contracts.md` §1.2 y §1.3.

---

## 3. Configuración Mínima

El módulo de telemetría del SDK vive en `sdk/piv_oac/telemetry/`. Si G-01 no ha integrado ese módulo todavía, la interfaz esperada es la definida a continuación — los consumidores deben importar desde esa ruta una vez que el módulo esté disponible.

```python
# Configuración recomendada
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc import (
    OTLPSpanExporter, OTLPMetricExporter
)

# Variables de entorno soportadas:
# OTEL_EXPORTER_OTLP_ENDPOINT — URL del collector (default: http://localhost:4317)
# OTEL_SERVICE_NAME            — nombre del servicio (default: piv-oac)
# PIV_OAC_TELEMETRY_ENABLED    — "true" | "false" (default: "false")
#                                Cuando es "false", toda la instrumentación es no-op.
#                                Esto garantiza que entornos sin collector no fallen.
```

**Uso del context manager de tracing:**

```python
from sdk.piv_oac.telemetry import setup_tracing, agent_span

# Inicializar una vez al arrancar el proceso orquestador
setup_tracing(service_name="piv-oac")

# Envolver cada invocación de agente
with agent_span(agent_type="SpecialistAgent", model="claude-sonnet-4-6", objective_id="obj-42"):
    result = invoke_agent(...)
```

Ver implementación completa en `sdk/piv_oac/telemetry/tracer.py`.

---

## 4. Dashboard Recomendado (Grafana)

Un dashboard operacional mínimo debe incluir los siguientes panels. El intervalo de consulta por defecto es las últimas 24 horas.

| Panel | Métrica base | Descripción |
|---|---|---|
| Gate approval rate por objetivo | `piv_oac.gate.duration_ms` + label `result` | Ratio `approved / (approved + rejected)` agrupado por `gate_name` y `objective_id` |
| Token consumption por agente y modelo | `piv_oac.agent.tokens` | Histograma desglosado por `agent_type`, `model`, `direction` (input/output) |
| Cost USD acumulado por objetivo | `piv_oac.objective.cost_usd` | Serie temporal acumulada, una línea por `objective_id` |
| Context usage % por agente | `piv_oac.context.usage_pct` | Gauge actual; línea de alerta en 70% (pre-warning) y 80% (VETO_SATURACIÓN threshold) |
| Agent failure rate (FAILURE_TYPE distribution) | `piv_oac.agent.invocations{result="failure"}` | Distribución de fallos por `agent_type`; tabla o pie chart |
| Gate duration p50 / p95 (ms) | `piv_oac.gate.duration_ms` | Percentiles p50 y p95 por `gate_name`; detecta gates lentos antes de GATE_DEADLOCK |

---

## 5. Alertas Críticas

Las siguientes cuatro alertas son obligatorias en cualquier entorno que ejecute objetivos Nivel 2 (según `skills/agent-contracts.md` y `skills/cost-control.md`).

### 5.1 Pre-VETO_SATURACIÓN

```
Condition:  piv_oac.context.usage_pct > 75
Severity:   WARNING
Message:    "Context usage for {agent_type} at {value}% — approaching VETO_SATURACIÓN threshold (80%)"
Action:     Notify orchestrator; do not halt yet. Halt is triggered at 80% per skills/cost-control.md.
```

### 5.2 GATE_DEADLOCK Warning

```
Condition:  count(piv_oac.gate.duration_ms{result="rejected"}) over same gate_name >= 3
              within a rolling window of the current objective
Severity:   WARNING
Message:    "Gate {gate_name} has rejected {count} consecutive times — GATE_DEADLOCK imminent"
Action:     Notify orchestrator immediately; per skills/fault-recovery.md §7, do not attempt a 4th iteration.
```

### 5.3 Budget Alert

```
Condition:  piv_oac.objective.cost_usd{objective_id} > budget_max * 0.8
Severity:   WARNING
Message:    "Objective {objective_id} has consumed {pct}% of budget ({usd} USD of {max} USD)"
Action:     MasterOrchestrator evaluates model downgrade per on_budget_80pct rule in skills/cost-control.md.
```

### 5.4 Reliability Alert

```
Condition:  rate(piv_oac.agent.invocations{result="failure"}[5m])
              / rate(piv_oac.agent.invocations[5m]) > 0.20
Severity:   CRITICAL
Message:    "Agent failure rate exceeds 20% over the last 5 minutes — pipeline reliability degraded"
Action:     Escalate to MasterOrchestrator; review FAILURE_TYPE distribution in dashboard panel §4.
```

---

## 6. Integración con agent-contracts.md

Cuando un agente emite su respuesta estructurada, debe también emitir su span de telemetría antes de retornar el control al orquestador invocante.

**Mapeo de campos de contrato a atributos OTel:**

| Campo de contrato (`skills/agent-contracts.md`) | Atributo OTel | Valor |
|---|---|---|
| `FAILURE_TYPE` presente en respuesta | `otel.status_code` | `ERROR` |
| `FAILURE_TYPE` valor | `error.type` | Valor exacto del campo (e.g., `GATE_DEADLOCK`) |
| `FAILURE_TYPE` ausente (respuesta exitosa) | `otel.status_code` | `OK` |
| `VERDICT: REJECTED` (SecurityAgent) | `gate.result` | `rejected` |
| `VERDICT: APPROVED` (SecurityAgent) | `gate.result` | `approved` |
| `AUDIT_RESULT: FAIL` (AuditAgent) | `gate.result` | `rejected` |
| `AUDIT_RESULT: PASS` (AuditAgent) | `gate.result` | `approved` |

**Regla de oro:** el span no debe cerrarse hasta que el agente haya emitido su bloque de contrato completo. Cerrar el span antes de que el agente termine su respuesta produce spans incompletos que no capturan tokens ni el estado final.

**Correlación con fault-recovery.md:** el campo `FAILURE_TYPE` definido en `skills/fault-recovery.md` §8.1 es el valor canónico que se propaga al atributo `error.type` del span. Los parsers del orquestador padre que extraen `FAILURE_TYPE` con el regex `^FAILURE_TYPE:\s+(.+)$` (per `skills/fault-recovery.md` §8.3) deben alimentar ese valor al SDK de telemetría inmediatamente después de parsear la respuesta.

---

## 7. Tabla de Referencia Cruzada

| Documento | Relación |
|---|---|
| `skills/agent-contracts.md` | Define los campos de contrato que se mapean a atributos OTel (§6 de este documento) |
| `skills/fault-recovery.md` | `FAILURE_TYPE` es el valor de `error.type` en el span; alerta 5.2 detecta GATE_DEADLOCK antes del umbral de §7 |
| `skills/cost-control.md` | `piv_oac.objective.cost_usd` y `piv_oac.context.usage_pct` implementan la observabilidad del presupuesto y del VETO_SATURACIÓN definidos allí |
| `sdk/piv_oac/telemetry/tracer.py` | Implementación del context manager `agent_span` y `setup_tracing` |
| `sdk/piv_oac/telemetry/__init__.py` | Exports públicos del módulo de telemetría |
