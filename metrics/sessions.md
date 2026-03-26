# Registro de Sesiones — Métricas PIV/OAC

Historial de objetivos ejecutados con métricas DORA-adaptadas.
Escritura delegada al AuditAgent al cierre de cada objetivo (FASE 8).
Lectura por Master Orchestrator al inicio de FASE 0 para calcular baseline.

> **Separación de esquemas:** este archivo registra métricas DORA de sesión completa (escritor: AuditAgent, FASE 8, append-only). Para el rubric de scoring 0-1 de expertos paralelos en tiempo real (escritor: EvaluationAgent, FASE 5b), ver `contracts/evaluation.md`. Los dos esquemas son independientes: no se mezclan ni se solapan.

---

## Plantilla de Entrada

```markdown
### OBJ-NNN — [Título del Objetivo]

| Campo | Valor |
|---|---|
| Fecha inicio | YYYY-MM-DD HH:MM UTC |
| Fecha cierre | YYYY-MM-DD HH:MM UTC |
| execution_mode | DEVELOPMENT / RESEARCH / MIXED |
| compliance_scope | FULL / MINIMAL / NONE |
| Resultado | COMPLETADO / ABANDONADO / BLOQUEADO |

#### Métricas de Entrega
| Métrica | Valor | Benchmark |
|---|---|---|
| Lead time (inicio → staging) | Xh Ym | <4h (simple) / <2d (complejo) |
| Deployment frequency | — | — |
| Gate pass rate (primera pasada) | X% | ≥80% objetivo |
| Iteraciones de gate promedio | X | ≤2 objetivo |

#### Métricas de Gate
| Gate | Resultado primera pasada | Iteraciones | Causa de rechazo (si aplica) |
|---|---|---|---|
| Gate Entorno | PASS / FAIL | X | — |
| Gate 1 (CoherenceAgent) | PASS / FAIL | X | — |
| Gate 2 (Security+Audit+Standards) | PASS / FAIL | X | — |
| Gate 3 (Humano) | PASS / FAIL | X | — |

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

#### Métricas de Contexto
| Métrica | Valor | Nota |
|---|---|---|
| Archivos cargados total | X | |
| Archivos cargados por experto (promedio) | X | Objetivo: ≤5 |
| Archivos únicos / total cargados | X% | Objetivo: ≥70% (baja redundancia) |
| Fragmentaciones realizadas | X | |

#### Incidencias
- (ninguna) o lista de BLOQUEADA_POR_DISEÑO / INVESTIGACIÓN_REQUERIDA / BLOQUEADO_POR_HERRAMIENTA ocurridas

#### Aprendizajes (AuditAgent)
- (átomos engram/ según dominio — ver engram/INDEX.md para tabla de acceso por agente)
```

---

## Sesiones Registradas

### OBJ-001 — piv-challenge v0.1.0 (PIV/OAC Adversarial Test Suite)

| Campo | Valor |
|---|---|
| Fecha inicio | 2026-03-16 (sesión multi-turno) |
| Fecha cierre | 2026-03-16 |
| execution_mode | DEVELOPMENT |
| compliance_scope | NONE |
| Resultado | COMPLETADO — Gate 3 APROBADO, mergeado a main 2026-03-16 |

#### Métricas de Entrega
| Métrica | Valor | Benchmark |
|---|---|---|
| Lead time (inicio → staging) | ~2 sesiones | <2d (complejo) ✓ |
| Gate pass rate (primera pasada) | 100% | ≥80% ✓ |
| Iteraciones de gate promedio | 1 | ≤2 ✓ |

#### Métricas de Gate
| Gate | Resultado primera pasada | Iteraciones | Causa de rechazo |
|---|---|---|---|
| Gate Entorno | N/A | — | Ciclo informal — agentes directos |
| Gate 1 (CoherenceAgent) | N/A | — | Ciclo informal |
| Gate 2 (Security+Audit+Standards) | PASS (herramientas) | 1 | — |
| Gate 3 (Humano) | PASS | 1 | — |

#### Métricas de Calidad (verificadas con herramientas)
| Métrica | Valor |
|---|---|
| Tests | 169 passed |
| Coverage | 98.29% |
| ruff errors | 0 |
| pip-audit | BLOQUEADO_POR_HERRAMIENTA (path con ñ) |
| RFs completados | 19/19 |
| Archivos | 67 nuevos |

#### Incidencias
- BLOQUEADO_POR_HERRAMIENTA: `pip-audit` — UnicodeDecodeError en path con `ñ`
- Inconsistencia de API en harnesses generados (`_call_agent` firma incorrecta) — detectada y corregida en misma sesión
- `pydantic==2.6.4` y `anthropic==0.25.0` requieren compilación Rust en Python 3.13 — corregido con versiones ≥2.7.0 / ≥0.40.0

#### Aprendizajes (engram)
- `ExpectedOutcome(str, Enum)` hace que `isinstance(val, str)` sea siempre True → usar `val in list(Enum)` para discriminar
- `ruff 0.1.6` no soporta `target-version = "py313"` → usar `py312` como proxy
- `setuptools.backends.legacy:build` eliminado en setuptools recientes → usar `setuptools.build_meta`

---

---

### OBJ-002 — PIV/OAC v3.3 Redesign Arquitectural

| Campo | Valor |
|---|---|
| Fecha inicio | 2026-03-22 |
| Fecha cierre | 2026-03-22 |
| execution_mode | DEVELOPMENT (MODO_META_ACTIVO) |
| compliance_scope | NONE |
| Resultado | COMPLETADO — Gate 3 APROBADO, mergeado a main 2026-03-22 |

#### Métricas de Entrega
| Métrica | Valor | Benchmark |
|---|---|---|
| Lead time total | ~4h (sesión única) | <4h (simple) ✓ |
| Tareas en DAG | 6 (T1→{T2,T3,T4,T5}→T6) | — |
| Gate pass rate (primera pasada) | 0% gate pre-código (plan v1) / 100% Gate 2 | ≥80% objetivo |
| Iteraciones de gate promedio | 2 (gate pre-código) / 1 (Gate 2, Gate 3) | ≤2 ✓ |

#### Métricas de Gate
| Gate | Resultado primera pasada | Iteraciones | Causa de rechazo (si aplica) |
|---|---|---|---|
| Gate pre-código plan v1 | FAIL | — | SecurityAgent: early termination sin contención + gap recovery AuditAgent |
| Gate pre-código plan v2 | PASS | 2 | — |
| Gate 2 (Security+Audit+Standards) | PASS | 1 | — |
| Gate 3 (Humano) | PASS | 1 | — |

#### Métricas de Calidad (verificadas con herramientas — MODO_META)
| Métrica | Valor | Fuente |
|---|---|---|
| Archivos creados | 12 | git log |
| Archivos modificados | 18 | git log |
| Archivos eliminados | 1 (security_auditor.md) | git log |
| Commits del objetivo | 6 | git log b3774e4..edf1843 |
| Cross-references válidas post-redesign | 26/26 | StandardsAgent Gate 2 |
| Referencias rotas | 0 | StandardsAgent Gate 2 Check 1 |
| Placeholders en framework | 0 | StandardsAgent Gate 2 Check 4 |
| RFs cumplidos | 7/7 objetivos del redesign | verificacion_intentos.txt |

#### Métricas de Costo
| Campo | Valor |
|---|---|
| tokens_input | N/D |
| tokens_output | N/D |
| tokens_total | N/D |
| usd_actual | N/D |
| usd_budget | N/D |
| budget_headroom_pct | N/D |

#### Métricas de Contexto
| Métrica | Valor | Nota |
|---|---|---|
| Archivos cargados total | ~12 | estimado de uso_contexto.txt |
| Archivos cargados por experto (promedio) | N/D | MODO_META — sin Specialists independientes |
| Worktrees activos | 0 | MODO_META — cambios directos en agent-configs |
| Fragmentaciones realizadas | 0 | sin VETO_SATURACIÓN emitido |

#### Incidencias
- Gate pre-código PLAN_VERSION 1 rechazado por SecurityAgent (2 bloqueantes): early termination sin contención y gap en recovery de AuditAgent. Resuelto en plan v2 sin escalado a usuario.
- EvaluationAgent no activado en esta sesión (sesión meta — no hay código de producto a evaluar).

#### Aprendizajes (AuditAgent)
- Patrón contracts/ como capa canónica registrado en engram/core/operational_patterns.md
- Gate decisions de esta sesión registradas en engram/audit/gate_decisions.md

---

## Baseline Agregado

| Métrica | Valor acumulado | Sesiones incluidas |
|---|---|---|
| Gate pass rate promedio | 50% primera pasada (1 fallo en OBJ-002 gate pre-código) | 2 |
| Lead time promedio | ~2 sesiones / ~4h | 2 |
| Fragmentaciones por objetivo | 0 | 2 |
| Contexto promedio por experto | N/A (OBJ-001: ciclo informal; OBJ-002: MODO_META) | 2 |
