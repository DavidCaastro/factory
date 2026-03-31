# METRICS — Esquema de Métricas PIV/OAC
> Escrito por: AuditAgent al cierre de cada objetivo (FASE 8).
> Lectura: Master Orchestrator para tendencias entre sesiones.
> Propósito: detectar degradación del proceso y medir mejoras reales entre versiones del framework.

---

## Métricas por Objetivo (registro por sesión)

Archivo de datos: `metrics/sessions.md` — append-only, mismo protocolo que logs_veracidad/.

```markdown
========== OBJETIVO [NOMBRE] — SESIÓN [TIMESTAMP] — RAMA [GIT] ==========

### Métricas de Entrega

| Métrica | Valor | Referencia industria |
|---|---|---|
| Lead time (turnos LISTA → COMPLETADA) | <n> turnos | — (baseline interno) |
| Tareas completadas / tareas totales | <n>/<n> | 100% ideal |
| Tareas BLOQUEADA_POR_DISEÑO | <n> | 0 ideal |
| Tareas INVESTIGACIÓN_REQUERIDA | <n> | — (informativo) |

### Métricas de Gates

| Métrica | Valor | Referencia industria |
|---|---|---|
| First-pass gate rate (aprobado en 1er intento) | <n>% | ≥ 80% como objetivo |
| Total de gates ejecutados | <n> | — |
| Total de rechazos | <n> | — |
| Agente con más rechazos | <nombre> | — (señal de área a mejorar) |
| Gates bloqueados por herramienta no disponible | <n> | 0 ideal |

### Métricas de Contexto

| Métrica | Valor | Referencia industria |
|---|---|---|
| Agentes creados | <n> | — |
| Fragmentaciones activadas | <n> | — |
| VETO_SATURACIÓN emitidos | <n> | 0 ideal |
| Archivos cargados por agente (promedio) | <n> | mínimo posible |

### Métricas de Calidad (DEVELOPMENT)

| Métrica | Valor | Umbral definido en skills/standards.md |
|---|---|---|
| Cobertura de tests (pytest-cov) | <n>% | según módulo |
| Errores ruff al cierre | <n> | 0 |
| CVEs detectados por pip-audit | <n> | 0 críticos |
| RFs incumplidos al cierre | <n> | 0 |

### Métricas de Calidad (RESEARCH — si aplica)

| Métrica | Valor | Referencia |
|---|---|---|
| RQs resueltas / RQs totales | <n>/<n> | 100% |
| RQs IRRESOLVABLE | <n> | documentadas con razón |
| Hallazgos confianza ALTA | <n>% | ≥ 60% como objetivo |
| Hallazgos confianza MEDIA | <n>% | — |
| Hallazgos confianza BAJA | <n>% | ≤ 20% como objetivo |
| Fuentes NO_VERIFICADAS detectadas | <n> | 0 en informe final |
```

---

## Índice de Sesiones

| Sesión | Objetivo | Fecha | First-pass rate | Tareas completadas | Resultado |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

---

## Protocolo de Interpretación

**First-pass gate rate < 80%:** Señal de que los planes llegan al gate sin suficiente preparación. Revisar si el Domain Orchestrator está cargando los skills correctos antes de planificar.

**Fragmentaciones frecuentes + VETO_SATURACIÓN > 0:** Señal de que el scope de las tareas es demasiado grande. Revisar criterios de descomposición del DAG.

**Gates bloqueados por herramienta > 0:** Señal de entorno roto o dependencias faltantes. Prioridad máxima — un gate sin herramienta es un gate sin enforcement.

**Confianza BAJA > 20% en RESEARCH:** Señal de RQs mal formuladas (demasiado amplias) o fuentes insuficientes en el dominio investigado.

**Tendencia de lead time creciente entre sesiones:** Señal de que la complejidad del framework está superando el beneficio. Revisar si la atomización condicional (agent.md §9) está siendo aplicada.

---

## Métricas de Evaluación (EvaluationAgent — por sesión)

Estas métricas se registran en metrics/sessions.md al cierre de cada sesión Nivel 2.
Fuente primaria: logs_scores/<session_id>.jsonl — nunca estimar.

| Métrica | Campo en JSONL | Descripción |
|---------|----------------|-------------|
| evaluation_experts_scored | COUNT(expert_id) por session | N expertos evaluados en la sesión |
| evaluation_winner_score | MAX(total_score) por session | Score del experto ganador |
| evaluation_score_spread | MAX - MIN de total_score | Diferencia entre mejor y peor score |
| early_terminations | COUNT(early_terminated=true) | N expertos terminados anticipadamente |
| precedent_registered | true/false | Si se registró precedente en esta sesión |
| precedent_score | total_score del ganador | Score del precedente (si se registró) |

Regla: Si logs_scores/ no existe o está vacío para la sesión → registrar N/D (herramienta no ejecutó).
Nunca inferir métricas de evaluación de la memoria del agente.

---

## Métricas para Objetivos de Framework (MODO_META_ACTIVO)

> Aplica cuando el objeto de trabajo es el propio framework (`agent-configs` o equivalente).
> Misma estructura append-only que las métricas de producto.

```markdown
========== OBJETIVO-FRAMEWORK [NOMBRE] — SESIÓN [TIMESTAMP] — RAMA [GIT] ==========

### Framework Quality Gate — Resultados

| Check | Resultado | Detalles |
|---|---|---|
| Cross-reference integrity | X/Y refs válidas | [lista de rotas si aplica] |
| Structural completeness | X/Y archivos completos | [lista de incompletos si aplica] |
| Protocol integrity | X/Y entradas canónicas | [lista de huérfanas si aplica] |
| No framework placeholders | X ocurrencias | [archivos con [PENDIENTE] si aplica] |

### Métricas de Proceso

| Métrica | Valor |
|---|---|
| Objetivos en la onda | [n] |
| Objetivos aprobados en primer intento de Gate 2 | [n] |
| Objetivos con re-gate requerido | [n] |
| Archivos modificados (total onda) | [n] |
| Commits generados | [n] |

### Gate 2 — Veredictos

| Agente | Veredicto | Re-gate requerido |
|---|---|---|
| SecurityAgent | APROBADO / RECHAZADO | SÍ / NO |
| AuditAgent | APROBADO / RECHAZADO | SÍ / NO |
| StandardsAgent | APROBADO / RECHAZADO | SÍ / NO |

========== FIN OBJETIVO-FRAMEWORK [NOMBRE] ==========
```

---

## Métricas de Eficiencia v4.0 (campos adicionales en la entrada de sesión)

### Métricas CSP

| Métrica | Campo | Descripción |
|---|---|---|
| CSP filter rate (promedio) | `csp_avg_filter_pct` | Promedio de % del artefacto filtrado en gates. Objetivo: ≥ 25% |
| CSP filter por gate | `csp_filter_pct_by_gate` | Objeto con filter_pct por cada gate ejecutado |

### Métricas PMIA

| Métrica | Campo | Descripción |
|---|---|---|
| Mensajes inter-agente | `pmia_messages_total` | Total de mensajes PMIA en la sesión |
| Reintentos PMIA | `pmia_retries` | Mensajes que requirieron retry por MALFORMED |
| Tasa de retry | `pmia_retry_rate` | pmia_retries / total × 100. Objetivo: ≤ 5% |

### Métricas de Tokens (ahora reales, no N/D)

| Métrica | Campo | Descripción |
|---|---|---|
| Tokens estimados | `tokens_estimated` | Del TokenBudgetReport de LogisticsAgent |
| Tokens reales | `tokens_actual` | Del ExecutionAuditReport — siempre real |
| Eficiencia | `token_efficiency_pct` | (actual/estimado) × 100. Objetivo: ≤ 120% |

### Métricas de Cumplimiento

| Métrica | Campo | Descripción |
|---|---|---|
| Gate compliance | `gate_compliance_rate` | % de gates sin irregularidades. Objetivo: 100% |
| Irregularidades críticas | `critical_irregularities` | Count de CRITICAL. Objetivo: 0 |
| Eventos de saturación | `context_saturation_events` | VETO_SATURACION emitidos. Objetivo: 0 |
