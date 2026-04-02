# Especificaciones Funcionales — PIV/OAC Framework v4.0

> Marco directivo de gobernanza de agentes LLM.
> Este documento define los Requisitos Funcionales (RFs) del framework v4.0.
> Estado: COMPLETADO — OBJ-003 entregado 2026-03-31 | Gate 3 APROBADO | commit bbc2e36

---

## RF-LOG-01: LogisticsAgent — Análisis Proactivo Pre-Instanciación

| Campo | Valor |
|---|---|
| Versión | v4.0 |
| Prioridad | ALTA |
| Estado | COMPLETADO |
| Evidencia | commit bbc2e36 — Gate 3 APROBADO 2026-03-31 |

**Descripción:** LogisticsAgent es un agente de análisis proactivo de recursos que se activa en FASE 1 (post-DAG, pre-presentación al usuario). Produce un `TokenBudgetReport` antes de que el Master presente el DAG al usuario. Usa el modelo claude-haiku-4-5. Tiene un presupuesto propio de 3.000 tokens, fuera del pool del objetivo.

**Token Caps absolutos:**

| Nivel de tarea | Cap de tokens |
|---|---|
| Nivel 1 | 8.000 |
| Nivel 2 (≤ 3 archivos) | 40.000 |
| Nivel 2 estándar | 100.000 |
| Nivel 2 (≥ 10 archivos) | 200.000 |

**Criterio de aceptación:** El TokenBudgetReport se genera correctamente para todo DAG de Nivel 2. La estimación por tarea incluye: `estimated_tokens`, `cap_applied`, `capped`, `file_count`, `dependency_count`, `recommended_expert_count`, `fragmentation_required`.

---

## RF-LOG-02: TokenBudgetReport en la Presentación del DAG

| Campo | Valor |
|---|---|
| Versión | v4.0 |
| Prioridad | ALTA |
| Estado | COMPLETADO |
| Evidencia | commit bbc2e36 — Gate 3 APROBADO 2026-03-31 |

**Descripción:** El TokenBudgetReport generado por LogisticsAgent se incluye obligatoriamente en la presentación del DAG al usuario cuando el objetivo es Nivel 2. El Master Orchestrator no presenta el DAG sin el informe adjunto en objetivos Nivel 2.

**Criterio de aceptación:** En toda ejecución Nivel 2, la presentación al usuario contiene: (1) el DAG, (2) el TokenBudgetReport con estimación total, (3) lista de tareas con `fragmentation_required=true` si aplica, (4) cualquier `WARNING_ANOMALOUS_ESTIMATE` activo.

---

## RF-LOG-03: WARNING_ANOMALOUS_ESTIMATE

| Campo | Valor |
|---|---|
| Versión | v4.0 |
| Prioridad | MEDIA |
| Estado | COMPLETADO |
| Evidencia | commit bbc2e36 — Gate 3 APROBADO 2026-03-31 |

**Descripción:** Cuando la estimación de LogisticsAgent supera el cap del nivel correspondiente, el informe registra un `WARNING_ANOMALOUS_ESTIMATE`. El Master presenta este warning al usuario antes de continuar. El warning no bloquea la ejecución — es una advertencia de scope.

**Criterio de aceptación:** El warning se reporta en el TokenBudgetReport con: task_id afectado, estimación calculada, cap aplicado, diferencia en tokens. El Master lo presenta al usuario de forma visible antes de solicitar confirmación del DAG.

---

## RF-EXEC-01: ExecutionAuditor — Observador Out-of-Band

| Campo | Valor |
|---|---|
| Versión | v4.0 |
| Prioridad | ALTA |
| Estado | COMPLETADO |
| Evidencia | commit bbc2e36 — Gate 3 APROBADO 2026-03-31 |

**Descripción:** ExecutionAuditor es un observador pasivo activo desde FASE 2 hasta FASE 8. No emite veredictos de gate. No interviene en el flujo de ejecución. Solo observa y registra. Detecta las siguientes irregularidades: `GATE_SKIPPED`, `GATE_BYPASSED`, `PROTOCOL_DEVIATION`, `TOKEN_OVERRUN`, `CONTEXT_SATURATION`, `UNAUTHORIZED_INSTANTIATION`. Usa claude-haiku-4-5 con presupuesto propio de 5.000 tokens.

**Criterio de aceptación:** ExecutionAuditor se instancia en toda ejecución Nivel 2. Registra todos los eventos de las fases 2-8 en `.piv/active/<objective_id>_audit_events.jsonl`. Al cierre de FASE 8, genera `ExecutionAuditReport` con todos los campos requeridos por `metrics/execution_audit_schema.md`.

---

## RF-EXEC-02: ExecutionAuditReport Siempre Generado

| Campo | Valor |
|---|---|
| Versión | v4.0 |
| Prioridad | ALTA |
| Estado | COMPLETADO |
| Evidencia | commit bbc2e36 — Gate 3 APROBADO 2026-03-31 |

**Descripción:** ExecutionAuditor genera su reporte final (`ExecutionAuditReport`) siempre al cierre, incluso si la ejecución principal falla. Su reporte es insumo del AuditAgent en FASE 8, no sustituto. Si ocurre un error interno del auditor, genera un reporte parcial con campo `error` — nunca propaga la excepción.

**Criterio de aceptación:** En toda ejecución Nivel 2 (exitosa o fallida), existe un `ExecutionAuditReport` al cierre de FASE 8. El reporte parcial tiene el campo `error` poblado en caso de fallo interno del auditor.

---

## RF-CSP-01: Context Scope Protocol — Almacenamiento Único en StateStore

| Campo | Valor |
|---|---|
| Versión | v4.0 |
| Prioridad | MEDIA |
| Estado | COMPLETADO |
| Evidencia | commit bbc2e36 — Gate 3 APROBADO 2026-03-31 |

**Descripción:** En gates con múltiples agentes revisando el mismo artefacto, el artefacto se almacena una sola vez en StateStore (genera `artifact_ref`). Cada agente recibe solo el scope filtrado según su checklist definido en `contracts/gates.md`. El agente puede solicitar contexto adicional vía `artifact_ref` si lo necesita.

**Criterio de aceptación:** En Gate 2 y Gate 2b, el artefacto no se duplica por agente. Cada agente recibe scope filtrado. El `artifact_ref` es válido durante toda la sesión del gate. Reducción estimada de tokens en gates: 30-50% vs sin CSP.

---

## RF-CSP-02: Scope Filters Canónicos por Agente

| Campo | Valor |
|---|---|
| Versión | v4.0 |
| Prioridad | MEDIA |
| Estado | COMPLETADO |
| Evidencia | commit bbc2e36 — Gate 3 APROBADO 2026-03-31 |

**Descripción:** Los scope filters canónicos por agente son: SecurityAgent = [auth, crypto, secrets, input_validation, permissions]; AuditAgent = [business_logic, tests, rf_coverage]; StandardsAgent = [tests, docstrings, imports, linting]. Estos filtros se definen en `contracts/gates.md`. Un agente puede solicitar más contexto vía `artifact_ref` si su scope filtrado es insuficiente.

**Criterio de aceptación:** Los scope filters están definidos en `contracts/gates.md` con las keywords canónicas. El GateEnforcer los aplica al distribuir el artefacto a cada agente. Un agente puede emitir `CONTEXT_REQUEST` con `artifact_ref` para obtener contexto adicional.

---

## RF-CSP-03: Razonamiento In-Agent — Solo Viaja el Veredicto

| Campo | Valor |
|---|---|
| Versión | v4.0 |
| Prioridad | MEDIA |
| Estado | COMPLETADO |
| Evidencia | commit bbc2e36 — Gate 3 APROBADO 2026-03-31 |

**Descripción:** El razonamiento (chain of thought) de un agente de gate es in-agent — no viaja en los mensajes inter-agente. Solo viaja el veredicto estructurado definido en `contracts/gates.md`. Reducción estimada de tokens en gates: 30-50% vs enviar razonamiento completo.

**Criterio de aceptación:** Los mensajes de veredicto de gate no contienen chain-of-thought. Solo contienen los campos del tipo `GATE_VERDICT` definido en `skills/inter-agent-protocol.md`. El GateEnforcer rechaza mensajes de veredicto que excedan 300 tokens.

---

## RF-PMIA-01: Protocolo de Mensaje Inter-Agente — 4 Tipos

| Campo | Valor |
|---|---|
| Versión | v4.0 |
| Prioridad | ALTA |
| Estado | COMPLETADO |
| Evidencia | commit bbc2e36 — Gate 3 APROBADO 2026-03-31 |

**Descripción:** Los mensajes entre agentes siguen el PMIA con 4 tipos: `GATE_VERDICT`, `ESCALATION`, `CROSS_ALERT`, `CHECKPOINT_REQ`. Máximo 300 tokens por mensaje. Sin chain-of-thought. Firma HMAC obligatoria. El contenido compartido viaja por `artifact_ref`, no por copia directa.

**Criterio de aceptación:** Todo mensaje inter-agente tiene: tipo válido, campos obligatorios del schema, firma HMAC, timestamp ISO8601. El receptor valida la estructura antes de procesar. Mensajes > 300 tokens son rechazados. Contenido de artefactos referenciado, no copiado.

---

## RF-PMIA-02: Retry Protocol PMIA

| Campo | Valor |
|---|---|
| Versión | v4.0 |
| Prioridad | MEDIA |
| Estado | COMPLETADO |
| Evidencia | commit bbc2e36 — Gate 3 APROBADO 2026-03-31 |

**Descripción:** El receptor valida la estructura del mensaje. Si detecta `MALFORMED_MESSAGE`: retorna el error al emisor, que reformatea y reenvía (máximo 2 reintentos). Si falla tras 2 reintentos: `ESCALATE` al Domain Orchestrator que coordina la comunicación. Máximo 2 reintentos para `MALFORMED_MESSAGE` (la regla de 3 reintentos con backoff aplica solo a `MessageExpired`).

**Criterio de aceptación:** El retry protocol está implementado. Tras 2 reintentos fallidos por `MALFORMED_MESSAGE`, se genera una `ESCALATION` al Domain Orchestrator. El ExecutionAuditor registra `pmia_retries` y `pmia_escalations` en el ExecutionAuditReport.

---

## RF-INHERIT-01: InheritanceGuard — SAFE_INHERIT Whitelist

| Campo | Valor |
|---|---|
| Versión | v4.0 |
| Prioridad | ALTA |
| Estado | COMPLETADO |
| Evidencia | commit bbc2e36 — Gate 3 APROBADO 2026-03-31 |

**Descripción:** Solo 5 atributos pueden heredarse de agente padre a hijo (SAFE_INHERIT): `objective_id`, `task_scope`, `execution_mode`, `compliance_scope`, `parent_agent_id`. Todo lo demás (permisos, credenciales, api_keys, capabilities) NO se hereda. Los permisos del hijo los asigna PermissionStore, nunca el padre. Profundidad máxima de herencia: 1 nivel (solo padre → hijo, sin cadenas recursivas).

**Criterio de aceptación:** InheritanceGuard filtra el contexto heredado a los 5 campos SAFE_INHERIT. Un intento de heredar permisos o credenciales genera un error `InheritanceViolation`. La profundidad `MAX_INHERITANCE_DEPTH = 1` se aplica en AgentFactory.

---

## RF-INHERIT-02: TTL y HMAC del Snapshot Heredado

| Campo | Valor |
|---|---|
| Versión | v4.0 |
| Prioridad | ALTA |
| Estado | COMPLETADO |
| Evidencia | commit bbc2e36 — Gate 3 APROBADO 2026-03-31 |

**Descripción:** El snapshot de contexto heredado tiene TTL de 30 minutos y firma HMAC. Un snapshot expirado genera `InheritanceExpired` (error esperado — solicitar snapshot fresco al factory). Un snapshot con firma inválida genera `InheritanceTampered` → `SECURITY_VIOLATION` inmediato.

**Criterio de aceptación:** El snapshot heredado incluye timestamp de creación y firma HMAC. CryptoValidator verifica TTL y firma antes de usarlo. `InheritanceExpired` y `InheritanceTampered` son errores tipados con acción definida.

---

## RF-SIGN-01: Code Signing de Skills

| Campo | Valor |
|---|---|
| Versión | v4.0 |
| Prioridad | ALTA |
| Estado | COMPLETADO |
| Evidencia | commit bbc2e36 — Gate 3 APROBADO 2026-03-31 |

**Descripción:** AtomLoader verifica el SHA-256 de cada skill contra `skills/manifest.json` antes de cargarlo. Hash incorrecto → `BLOQUEADO_POR_HERRAMIENTA` (se notifica al usuario). Si el skill no está en el manifest → `BLOQUEADO_POR_HERRAMIENTA`. Solo StandardsAgent con permiso `skill:write` (concedido post-gate SecurityAgent con confirmación humana) puede actualizar el manifest. El permiso expira en 30 minutos.

**Criterio de aceptación:** AtomLoader no carga ningún skill sin verificar su SHA-256 contra el manifest. El script `scripts/skill_manifest.py --verify` sale con código 0 cuando todos los hashes son correctos. Solo StandardsAgent con `skill:write` puede actualizar el manifest.

---

## RF-METRICS-01: RealtimeMetrics Siempre Activo

| Campo | Valor |
|---|---|
| Versión | v4.0 |
| Prioridad | MEDIA |
| Estado | COMPLETADO |
| Evidencia | commit bbc2e36 — Gate 3 APROBADO 2026-03-31 |

**Descripción:** RealtimeMetrics captura tokens y costo por agente en tiempo real, en cada llamada al LLM. No requiere infraestructura externa. Genera alertas al 75% del presupuesto configurado (WARNING al MasterOrchestrator) y al 90% (CRITICAL — presentar al usuario antes de continuar).

**Criterio de aceptación:** RealtimeMetrics captura `tokens_input`, `tokens_output`, `cost_usd` y `context_window_pct` por agente. Las alertas al 75% y 90% se generan correctamente. El snapshot final de RealtimeMetrics se incluye en el ExecutionAuditReport.

---

## RF-METRICS-02: ExecutionAuditReport — Campos Requeridos

| Campo | Valor |
|---|---|
| Versión | v4.0 |
| Prioridad | MEDIA |
| Estado | COMPLETADO |
| Evidencia | commit bbc2e36 — Gate 3 APROBADO 2026-03-31 |

**Descripción:** El ExecutionAuditReport generado por ExecutionAuditor incluye obligatoriamente: `total_events`, `total_irregularities`, `critical_irregularities`, `gate_compliance_rate`, `tokens_per_agent`, `pmia_messages_total`, `pmia_retries`, `pmia_retry_rate`, `summary`. Disponible al cierre de cualquier ejecución Nivel 2.

**Criterio de aceptación:** El schema completo está definido en `metrics/execution_audit_schema.md`. El reporte generado pasa validación contra ese schema. El campo `summary` tiene menos de 100 tokens.

---

## RF-LOGS-01: logs_veracidad/ Organizado por Producto

| Campo | Valor |
|---|---|
| Versión | v4.0 |
| Prioridad | MEDIA |
| Estado | COMPLETADO |
| Evidencia | commit bbc2e36 — Gate 3 APROBADO 2026-03-31 |

**Descripción:** El directorio `logs_veracidad/` se organiza por producto. Estructura: `logs_veracidad/_global/` para eventos del framework en sí (intent rejections, cambios meta) y `logs_veracidad/<product-id>/` para eventos de cada producto/objetivo. Formato JSONL append-only con timestamp ISO8601 en cada línea.

**Criterio de aceptación:** El directorio `_global/` existe con `framework_events.jsonl` e `intent_rejections.jsonl`. Para cada objetivo Nivel 2, existe `logs_veracidad/<objective_id>/` con los 3 archivos JSONL: `acciones.jsonl`, `uso_contexto.jsonl`, `verificacion_rf.jsonl`.

---

## RF-LOGS-02: Schema JSONL de Logs

| Campo | Valor |
|---|---|
| Versión | v4.0 |
| Prioridad | MEDIA |
| Estado | COMPLETADO |
| Evidencia | commit bbc2e36 — Gate 3 APROBADO 2026-03-31 |

**Descripción:** Cada línea JSONL de logs incluye obligatoriamente: `ts` (ISO8601), `session` (objective_id), `agent`, `event`, y los campos específicos del tipo de evento. El schema canónico está definido en `metrics/execution_audit_schema.md`. Los logs son append-only — nunca se sobreescriben.

**Criterio de aceptación:** Todo evento escrito en logs_veracidad/ incluye los 4 campos base (ts, session, agent, event). El formato es JSON válido por línea (JSON Lines). El modo de escritura es siempre append — nunca write/overwrite. El AuditAgent registra el SHA-256 del archivo al cierre en `engram/audit/gate_decisions.md`.
