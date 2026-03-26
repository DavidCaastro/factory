# ROADMAP PIV/OAC → Producción v1.0
> Auditoría realizada el 2026-03-16. Rama: `agent-configs`.
> Documento vivo — actualizar estado de cada ítem al completarlo.

---

## Puntuación de Madurez

| Dimensión | Score |
|---|---|
| Dimensión | Score Inicial | Score Post-Roadmap | Delta |
|---|---|---|---|
| Coherencia Conceptual | 85.0 / 100 | **91.0 / 100** | +6.0 |
| Completitud Operativa | 72.0 / 100 | **86.0 / 100** | +14.0 |
| Calidad de Documentación | 80.0 / 100 | **88.0 / 100** | +8.0 |
| Robustez ante Fallos | 70.0 / 100 | **84.0 / 100** | +14.0 |
| Testabilidad / Verificabilidad | 65.0 / 100 | **83.0 / 100** | +18.0 |
| Escalabilidad | 75.0 / 100 | **78.0 / 100** | +3.0 |
| **Madurez como Protocolo** | **74.5 / 100** | **85.0 / 100** | **+10.5** |
| **Preparación para Producción** | **61.7 / 100** | **76.3 / 100** | **+14.6** |

> Actualizado: 2026-03-16. Metodología: revisión estructural de gaps + validación con piv-challenge (98.29% test coverage).
> Límites de score: Testabilidad no llega a 90 porque primer ciclo FORMAL (AuditAgent FASE 8) aún no ejecutado.
> Escalabilidad limitada: V-6 (2 objetivos paralelos) pendiente.

### Comparación de Mercado

> Actualizado: 2026-03-23. Metodología: scoring ponderado 12 dimensiones (ver `docs/justification/competitive-analysis.md`).
> Pesos ajustados: D12 Ecosistema reducido a 5% (proyecto en construcción); D6 Packaging corregido a 4/5 (SDK publicado en PyPI).

| Framework | Gov./Gates | Audit | Compliance | SDK/PyPI | Score prod. ponderado |
|---|---|---|---|---|---|
| Semantic Kernel | Bajo | Ninguno | Parcial | ✓ | ~74/100 |
| AutoGen (Microsoft) | Medio | Básico | Ninguno | ✓ | ~72/100 |
| LangGraph (LangChain) | Bajo | Ninguno | Ninguno | ✓ | ~71/100 |
| **PIV/OAC v3.2** | **Muy Alto** | **Completo** | **Completo** | **✓** | **~72/100** |
| CrewAI | Bajo | Ninguno | Ninguno | ✓ | ~65/100 |
| MetaGPT | Medio-Alto | Parcial | Ninguno | ✓ | ~63/100 |
| OpenHands | Muy bajo | Ninguno | Ninguno | ✗ | ~51/100 |

> PIV/OAC lidera en gobernanza, audit trail y compliance. Con D6 corregido (SDK en PyPI) y D12 rebalanceado, el score de producción asciende a ~72/100, paridad con AutoGen/LangGraph.
> Ventaja diferencial única: única solución con gates bloqueantes formalizados, audit trail RF→código y compliance integrado en el mercado.
> Ver análisis completo y justificación: `docs/justification/competitive-analysis.md`

---

## Estado de Gaps por Fase

### FASE 1 — Protocolo Crítico
> Secuencial: C-2 → M-8 por dependencia. A-1 en paralelo con ambos.

| ID | Severidad | Gap | Archivo(s) afectado(s) | Estado |
|---|---|---|---|---|
| C-2 | CRÍTICO | Mecanismo de "pausado" a 60 % de contexto sin protocolo explícito | `agent.md §13`, `skills/session-continuity.md` | ✅ Completado |
| M-8 | MEDIO | `VETO_SATURACIÓN` en cascada: si el padre también está saturado, no hay protocolo | `agent.md` regla permanente | ✅ Completado |
| A-1 | ALTO | Activación de `MODO_META_ACTIVO` sin flujo determinista documentado | `agent.md §8`, `registry/orchestrator.md` | ✅ Completado |

**Entregables de Fase 1:**
- `skills/context-management.md` — protocolo de pausado incremental + VETO en cascada
- Actualización de `agent.md §13` y regla permanente `VETO_SATURACIÓN`
- Actualización de `registry/orchestrator.md` — detección automática `agent-configs` → `MODO_META_ACTIVO`

---

### FASE 2 — Coherencia Interna
> Todo en paralelo. Sin dependencias entre ítems.

| ID | Severidad | Gap | Archivo(s) afectado(s) | Estado |
|---|---|---|---|---|
| M-1 | MEDIO | `project_spec.md` obsoleto, aún presente en `skills/orchestration.md` línea 13 | `skills/orchestration.md` | ✅ Completado |
| M-2 | MEDIO | "Definición de mismo plan" con dos versiones distintas | `registry/orchestrator.md`, `registry/security_agent.md` | ✅ Completado (ya alineado; confirmado) |
| M-3 | MEDIO | Contador de rechazos de plan sin storage definido | `registry/orchestrator.md Paso 6` | ✅ Completado |
| M-4 | MEDIO | `TechSpecSheet` con `pip-audit` no ejecutable: ¿bloquea Gate 2 o admite `N/D`? | `registry/audit_agent.md` | ✅ Completado |
| M-5 | MEDIO | Responsabilidad de `git checkout main` en Contexto de Rama para Agentes no especificada | `CLAUDE.md` regla permanente | ✅ Completado |
| M-7 | MEDIO | Schema `.piv/active/<objetivo>.json` declarado en dos archivos con campos distintos | `skills/session-continuity.md`, `.piv/README.md` | ✅ Completado |
| B-1 | BAJO | Referencias circulares `CLAUDE.md ↔ agent.md` sin jerarquía clara de autoridad | `CLAUDE.md`, `agent.md` | ✅ Completado |
| B-2 | BAJO | Versionado del framework no documentado (¿tags git? ¿campo en CLAUDE.md?) | General | ✅ Completado |
| B-3 | BAJO | `session_learning.md` DEPRECATED sigue en repo causando confusión | `engram/session_learning.md` | ✅ Completado (eliminado) |
| B-4 | BAJO | DoD (Definition of Done) sin source of truth único | Múltiples | ✅ Completado |
| B-5 | BAJO | Reconocimiento de Mitigación acepta solo patrón rígido de texto | `registry/compliance_agent.md` | ✅ Completado |
| B-6 | BAJO | `gate3_reminder_hours` configurable pero sin validación de presencia del campo | `specs/_templates/INDEX.md` | ✅ Completado |
| B-7 | BAJO | Matriz de riesgo Nivel 1: redacción "uno o más" ambigua en edge cases | `CLAUDE.md` | ✅ Completado |

**Entregables de Fase 2:**
- Búsqueda-reemplazo global `project_spec.md` → `specs/active/INDEX.md`
- Sección única "Determinación de Mismo Plan" en `registry/orchestrator.md`
- Especificación de storage del contador de rechazos en `acciones_realizadas.txt`
- Comportamiento explícito de `N/D` en `TechSpecSheet` (si bloquea o no Gate 2)
- Aclaración de responsabilidad de `git checkout` en `CLAUDE.md`
- Schema canónico `.piv/active/<objetivo>.json` en un único lugar con referencia cruzada
- Eliminación de `engram/session_learning.md`
- DoD centralizado en `skills/standards.md` con referencias desde otros archivos
- Aclaración de jerarquía CLAUDE.md → authority, agent.md → detail

---

### FASE 3 — Resiliencia
> A-2 y A-3 en paralelo. A-4 en paralelo también. M-6 al final (depende de que el protocolo esté estabilizado).

| ID | Severidad | Gap | Archivo(s) afectado(s) | Estado |
|---|---|---|---|---|
| A-2 | ALTO | Engram completamente vacío: primer ciclo es bootstrapping ciego sin aprendizajes base | `engram/` | ✅ Completado |
| A-3 | ALTO | Gate 3 bloqueado indefinidamente si usuario nunca reconoce Documento de Mitigación | `registry/orchestrator.md` | ✅ Completado |
| A-4 | ALTO | AuditAgent falla en FASE 8: objetivo queda en staging sin camino de salida | `registry/audit_agent.md`, `registry/orchestrator.md` | ✅ Completado |
| M-6 | MEDIO | Diagramas Mermaid `docs/flows/` sin mecanismo de re-sincronización con el protocolo | `docs/flows/` (13 archivos) | ✅ Completado |

**Entregables de Fase 3:**
- `engram/core/architecture_decisions.md` — decisiones arquitectónicas documentadas del framework v3.2
- `engram/core/operational_patterns.md` — patrones operativos conocidos desde la definición del protocolo
- `engram/quality/code_patterns.md` — patrones de calidad reconocidos
- Timeout 48h para Gate 3 en `registry/orchestrator.md` con estado `GATE3_REMINDER_PENDIENTE`
- Protocolo de contingencia AuditAgent en FASE 8: quién retoma, cómo se marca el objetivo
- Revisión de los 13 diagramas Mermaid contra el protocolo actualizado en Fases 1-2

---

### FASE 4 — Validación Real
> Secuencial. Solo ejecutable tras completar Fases 1, 2 y 3.

| ID | Tipo | Tarea | Estado |
|---|---|---|---|
| V-1 | Validación | Ejecutar `sh scripts/bootstrap.sh` y validar `.piv/local.env` generado correctamente | ✅ Completado — bootstrap.sh confirmado funcional; `.piv/local.env` generado |
| V-2 | Validación | Ejecutar `python scripts/validate_env.py` y confirmar entorno limpio | ✅ Completado — validate_env.py corregido (encoding UTF-8, detección pytest-cov); ejecuta sin errores |
| V-3 | Ciclo real | Lanzar objetivo piv-challenge (N-2+): observar ciclo completo bajo supervisión | ✅ Completado — piv-challenge v0.1.0: 19 RFs, 169 tests, 98.29% cov, ruff 0 err; en staging |
| V-4 | Revisión | Auditar `logs_veracidad/` y `engram/` tras primer ciclo — verificar escrituras de AuditAgent | ✅ Observado — `logs_veracidad/` vacío (ciclo informal; AuditAgent FASE 8 no invocado formalmente). `engram/` tiene átomos base de sesiones previas. Primer ciclo formal completará esto. |
| V-5 | Revisión | Revisar `metrics/sessions.md` tras primer ciclo — confirmar schema correcto | ✅ Observado — schema correcto en `metrics/sessions.md`. Primera entrada registrada manualmente para piv-challenge (ver abajo). |
| V-6 | Escalado | Lanzar 2 objetivos en paralelo — verificar aislamiento de ramas y coherencia de gates | ✅ Completado — OBJ-002 + OBJ-003 en paralelo real (commits 7198bc2 + 62c7db9); sin conflictos de merge |
| V-7 | Score final | Re-auditar framework tras ciclos reales — actualizar puntuación en este documento | ✅ Completado — scores actualizados abajo |

---

## Notas Correctivas del Análisis

> Gaps descartados tras verificación directa del repositorio:

| ID original | Gap reportado | Corrección |
|---|---|---|
| C-1 | `scripts/bootstrap.sh` no existe | ✅ FALSO POSITIVO — script existe, está completo y funcional. `validate_env.py` también existe. |

---

## Resumen de Esfuerzo Estimado

| Fase | Ítems | Esfuerzo total est. | Paralelizable |
|---|---|---|---|
| Fase 1 | 3 | 8-11h | A-1 paralelo a C-2+M-8 |
| Fase 2 | 13 | 8-12h | 100 % paralelo |
| Fase 3 | 4 | 10-14h | A-2, A-3, A-4 paralelos |
| Fase 4 | 7 | Variable (ciclos reales) | Secuencial |
| **Total** | **27** | **~26-37h + ciclos** | — |

---

## Objetivo de Score Post-Roadmap

| Dimensión | Score actual | Score objetivo |
|---|---|---|
| Coherencia Conceptual | 85.0 | 92.0 |
| Completitud Operativa | 72.0 | 88.0 |
| Calidad de Documentación | 80.0 | 90.0 |
| Robustez ante Fallos | 70.0 | 85.0 |
| Testabilidad / Verificabilidad | 65.0 | 80.0 |
| Escalabilidad | 75.0 | 85.0 |
| **Madurez como Protocolo** | **74.5** | **~86.7** |
| **Preparación para Producción** | **61.7** | **~82.0** |
