# SPECS — Índice de Módulos (Contrato de Ejecución)
> Este archivo es el único que el Master Orchestrator lee en el primer paso de FASE 1.
> A partir de este índice determina qué módulos cargar, para qué agente, y cuándo.
> Escritura: generado manualmente con confirmación humana. Inmutable durante ejecución activa.

---

## Identidad del Proyecto

| Atributo | Valor |
|---|---|
| Nombre | PIV/OAC Framework v4.0 |
| Versión activa | v4.0.0 |
| Stack principal | Markdown, JSON, Python (scripts de automatización) |
| Mercado objetivo | Uso interno — marco directivo de gobernanza de agentes LLM |
| Tipo de producto | Marco directivo — archivos de gobernanza de agentes LLM |
| execution_mode | DEVELOPMENT |
| compliance_scope | MINIMAL |
| gate3_reminder_hours | 24 |
| Fecha de inicio | 2026-03-31 |
| Última actualización | 2026-04-02 |

---

## Tabla de Módulos y Carga por Agente

| Módulo | Agente que lo carga | Cuándo | Modo activo |
|---|---|---|---|
| `specs/active/functional.md` | Master Orchestrator, AuditAgent, Domain Orchestrators | Inicio de objetivo DEVELOPMENT | DEVELOPMENT |
| `specs/active/architecture.md` | Master Orchestrator, Domain Orchestrators | Construcción del DAG | DEVELOPMENT |
| `specs/active/quality.md` | StandardsAgent, LogisticsAgent | Gate 2b + análisis de presupuesto | DEVELOPMENT |
| `specs/active/security.md` | SecurityAgent, ExecutionAuditor | Todos los gates + observación OOB | TODOS |

> `compliance.md` no se crea: `compliance_scope: MINIMAL` — herramienta interna sin datos de usuario.
> ComplianceAgent activo solo para verificación de licencias de dependencias.

---

## Estado del Objetivo Activo

| Atributo | Valor |
|---|---|
| Objetivo en curso | — (sin objetivo activo) |
| RFs en scope | — |
| Estado | COMPLETADO |
| Última ejecución completada | OBJ-003 — 2026-03-31 20:01 UTC |
| Commit de entrega | bbc2e36 (Gate 3 APROBADO) / 0fcca1d (cierre FASE 8) |

---

## Reglas de Inmutabilidad

Los archivos de `specs/active/` son el contrato de ejecución. **Inmutables durante la ejecución de un objetivo activo.**

1. Modificación con tarea activa → notificar al Master Orchestrator → detiene ejecución → acepta cambio → reconstruye DAG
2. Cambio que altera scope de tareas en progreso → notificar al usuario antes de continuar
3. Cambio sin objetivo activo → libre, no requiere gate

---

## Historial de Versiones del Contrato

| Versión | Fecha | Cambio principal |
|---|---|---|
| v4.0.0 | 2026-03-31 | Actualización marco directivo v3.2 → v4.0. Nuevos agentes: LogisticsAgent, ExecutionAuditor. Nuevos protocolos: CSP, PMIA, InheritanceGuard, CodeSigning. |
| v3.2.0 | 2026-03-30 | Inicialización del proyecto PIV/OAC SDK v4.0 |
