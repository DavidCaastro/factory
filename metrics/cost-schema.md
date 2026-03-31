# Métricas de Costo — Schema y Benchmarks

## Propósito
Define el schema de costo USD por objetivo y los benchmarks de referencia.
AuditAgent extiende cada entrada de `sessions.md` con la sección `cost` al cerrar un objetivo.

---

## Schema de Costo (extensión de sessions.md)

Agregar al final de cada entrada de `sessions.md`:

```markdown
#### Métricas de Costo
| Campo | Valor |
|---|---|
| tokens_input | 0 |
| tokens_output | 0 |
| tokens_total | 0 |
| usd_actual | $0.00 |
| usd_budget | $0.00 |
| budget_headroom_pct | 0% |

#### Distribución de Modelo
| Modelo | % tokens input | % tokens output | USD estimado |
|---|---|---|---|
| claude-opus-4-6 | 0% | 0% | $0.00 |
| claude-sonnet-4-6 | 0% | 0% | $0.00 |
| claude-haiku-4-5 | 0% | 0% | $0.00 |

#### Costo por Agente
| Agente | Tokens input | Tokens output | USD |
|---|---|---|---|
| MasterOrchestrator | 0 | 0 | $0.00 |
| SecurityAgent | 0 | 0 | $0.00 |
| AuditAgent | 0 | 0 | $0.00 |
| CoherenceAgent | 0 | 0 | $0.00 |
| DomainOrchestrators (total) | 0 | 0 | $0.00 |
| SpecialistAgents (total) | 0 | 0 | $0.00 |
```

---

## Fórmula de Cálculo

```python
# Precios lista Anthropic (actualizar si cambian)
PRICES = {
    "claude-opus-4-6":    {"input": 15.00, "output": 75.00},   # USD/M tokens
    "claude-sonnet-4-6":  {"input":  3.00, "output": 15.00},
    "claude-haiku-4-5":   {"input":  0.25, "output":  1.25},
}

def calc_usd(model: str, tokens_in: int, tokens_out: int) -> float:
    p = PRICES[model]
    return (tokens_in * p["input"] + tokens_out * p["output"]) / 1_000_000
```

---

## Benchmarks de Referencia

Basados en la POC activa y estimaciones del mercado:

| Tipo de objetivo | Tokens input típicos | Tokens output típicos | USD típico | USD máximo recomendado |
|---|---|---|---|---|
| Nivel 1 — micro-tarea | 5 000 – 15 000 | 2 000 – 6 000 | $0.05 – $0.30 | $1.00 |
| Nivel 2 — feature simple (1 DO, 2 expertos) | 50 000 – 120 000 | 20 000 – 50 000 | $1.00 – $3.50 | $8.00 |
| Nivel 2 — feature compleja (3+ DOs, 6+ expertos) | 200 000 – 500 000 | 80 000 – 200 000 | $5.00 – $18.00 | $30.00 |
| POC completa (como piv-challenge) | ~400 000 | ~150 000 | ~$12.00 | $25.00 |

**Alertas automáticas:**
- Al 60%: checkpoint de engram
- Al 80%: VETO_SATURACIÓN — detener nuevos agentes, notificar al usuario
- Al 95%: downgrade automático de modelos (Opus→Sonnet, Sonnet→Haiku)

---

## Costo por RF — Métrica de Eficiencia

Permite comparar eficiencia entre objetivos:

```
costo_por_rf = usd_actual / n_rfs_completados
```

| Objetivo | RFs completados | USD actual | USD/RF |
|---|---|---|---|
| OBJ-001 piv-challenge | 19 | (pendiente registro) | — |

Benchmark de mercado: LangGraph/AutoGen reportan $0.50–$2.00/RF en proyectos MVP.
Target PIV/OAC: ≤ $1.50/RF con lazy loading activo.

---

## Actualización de Precios

Los precios de referencia deben actualizarse al inicio de cada sprint si Anthropic modifica su pricing.
Responsable: operador humano del marco (actualizar este archivo + `skills/cost-control.md`).
