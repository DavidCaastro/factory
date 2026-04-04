# Contracts — Model Assignment
> Fuente canónica de asignación de modelos por agente en el framework PIV/OAC.
> La tabla de "Asignación de Modelo" en CLAUDE.md referencia este archivo.
> Versión: 2.0 | Actualizado en: OBJ-003 upgrade v4.0

---

## Tabla de Asignación

| Agente | Modelo | Razón |
|--------|--------|-------|
| Master Orchestrator | claude-opus-4-6 | Coordinación compleja, decisiones de DAG, veto ético |
| SecurityAgent | claude-opus-4-6 | Veto crítico, razonamiento de seguridad de alta precisión |
| AuditAgent | claude-haiku-4-5 (rutinario) / claude-sonnet-4-6 (escalado) | RF coverage con checklist predefinido — output totalmente estructurado. Escalar a Sonnet si conflicto MAYOR o CRÍTICO |
| CoherenceAgent | claude-haiku-4-5 (Gate 1) / claude-sonnet-4-6 (conflictos CRÍTICO) | Análisis de diffs con criterios fijos. Escalar a Sonnet cuando `conflict_type=CRITICAL` |
| Domain Orchestrators | claude-sonnet-4-6 | Coordinación de dominio, gestión de worktrees |
| StandardsAgent | claude-sonnet-4-6 | Calidad, linting, verificación de documentación |
| ComplianceAgent | claude-sonnet-4-6 | Checklists de compliance, análisis legal |
| EvaluationAgent | claude-sonnet-4-6 | Scoring 0-1, comparación de outputs de expertos |
| Specialist Agents | claude-sonnet-4-6 / claude-haiku-4-5 según complejidad atómica | Ver criterios abajo |
| DocumentationAgent | claude-haiku-4-5 (estructurado) / claude-sonnet-4-6 (inferencia de diseño) | Ver criterios abajo |
| LogisticsAgent | claude-haiku-4-5 | Estimación heurística pre-ejecución — no requiere razonamiento complejo. Ver: registry/logistics_agent.md |
| ExecutionAuditor | claude-haiku-4-5 | Observación pasiva y registro de eventos — output totalmente predefinido. Ver: registry/execution_auditor.md |

---

## Criterios de Selección por Nivel de Complejidad

### claude-opus-4-6 — Decisiones críticas y orquestación global
Usar cuando:
- La tarea requiere decisiones de arquitectura que afectan el objetivo completo
- Se ejerce un veto que puede detener toda la ejecución
- Se requiere coordinación de múltiples agentes y dominios simultáneamente
- La ambigüedad semántica es alta y el error tiene consecuencias irrecuperables

Agentes que siempre usan Opus: Master Orchestrator, SecurityAgent.

### claude-sonnet-4-6 — Coordinación, síntesis y análisis moderado
Usar cuando:
- La tarea requiere razonamiento estructurado con output bien definido
- Se coordinan expertos dentro de un dominio acotado
- Se producen logs, checklists o informes con criterios preestablecidos
- Se analizan diffs, trazabilidad o coherencia entre artefactos

Agentes que siempre usan Sonnet: Domain Orchestrators, StandardsAgent, ComplianceAgent, EvaluationAgent.
Agentes que usan Sonnet como escalado: AuditAgent (conflicto MAYOR/CRÍTICO), CoherenceAgent (conflict_type=CRITICAL).

### claude-haiku-4-5 — Tareas atómicas con instrucciones específicas y output estructurado
Usar cuando:
- La tarea tiene instrucciones muy precisas y un output totalmente predefinido
- No hay ambigüedad de diseño — solo ejecución de un patrón conocido
- El volumen de trabajo lo justifica (muchos archivos de documentación similar)
- El error no tiene consecuencias irreversibles en el objetivo

Agentes que siempre usan Haiku: LogisticsAgent, ExecutionAuditor, AuditAgent (rutinario), CoherenceAgent (Gate 1 estándar).
Agentes que pueden usar Haiku: Specialist Agents (complejidad baja), DocumentationAgent (modo estructurado).

### Specialist Agents — Criterio de selección

| Complejidad de la tarea atómica | Modelo |
|---|---|
| Arquitectura nueva, múltiples dependencias, decisiones de diseño | claude-sonnet-4-6 |
| Implementación con patrón conocido, ≤3 archivos, sin ambigüedad | claude-haiku-4-5 |

### DocumentationAgent — Criterio de selección

| Tipo de documentación | Modelo |
|---|---|
| Generación estructurada (README, deployment, referencia de API con template) | claude-haiku-4-5 |
| Inferencia de diseño (documentar decisiones arquitectónicas sin template completo) | claude-sonnet-4-6 |

---

## Reglas de Escalado de Modelo

### Escalado hacia arriba (upgrade)
Si cualquier agente detecta que su tarea supera su capacidad cognitiva o su ventana de contexto alcanza el 80% sin poder fragmentar → emitir `VETO_SATURACIÓN` y escalar al orquestador padre antes de continuar. El orquestador padre puede reasignar la tarea a un agente de modelo superior.

**Nunca continuar con una tarea que supera la capacidad del modelo asignado sin escalar.**

### Escalado en cascada
Si el orquestador padre también está saturado (≥80% de ventana) → escalar con `VETO_SATURACIÓN_CASCADA` hasta el Master Orchestrator. El Master Orchestrator presenta opciones al usuario.

Protocolo completo de saturación: `skills/context-management.md §4`.

### Degradación hacia abajo (downgrade)
Un Domain Orchestrator puede asignar Haiku a un Specialist Agent si:
1. La tarea atómica es claramente de complejidad baja (criterio de tabla arriba)
2. El plan ya fue aprobado por Gate 2 y el scope está completamente acotado
3. El Domain Orchestrator confirma que no hay ambigüedad de diseño en la tarea

**Un agente nunca se autodegrada — la asignación la hace el Domain Orchestrator.**

---

## Registro de Versiones

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-03-22 | Creación inicial — extraído de CLAUDE.md + adición de EvaluationAgent |
| 2.0 | 2026-04-02 | v4.0: añadidos LogisticsAgent (haiku) y ExecutionAuditor (haiku) |
| 3.0 | 2026-04-04 | Auditoría coste: AuditAgent y CoherenceAgent migrados a haiku por defecto; sonnet como escalado para conflictos MAYOR/CRÍTICO |
