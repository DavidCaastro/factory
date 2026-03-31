# SPECS — Índice de Módulos (Contrato de Ejecución)
> Este archivo es el único que el Master Orchestrator lee en el primer paso de FASE 1.
> A partir de este índice determina qué módulos cargar, para qué agente, y cuándo.
> Escritura: generado por INIT (skills/init.md) con confirmación humana. Inmutable durante ejecución activa.

---

> **PROPÓSITO DE ESTE ARCHIVO**
> Punto de entrada único del framework para cualquier objetivo. Define identidad del proyecto,
> modo de operación y estado del objetivo activo. Si un campo está en `[PENDIENTE]` el Master
> Orchestrator no puede construir el DAG — INIT debe completarlo primero.
> Los paths de módulos apuntan a `specs/active/` — nunca a `specs/_templates/`.

---

## Identidad del Proyecto

| Atributo | Valor |
|---|---|
| Nombre | [PENDIENTE] |
| Versión activa | v0.1 |
| Stack principal | [PENDIENTE] |
| Mercado objetivo | [PENDIENTE] |
| Tipo de producto | [PENDIENTE] |
| execution_mode | INIT |
| compliance_scope | [PENDIENTE] |
| gate3_reminder_hours | 24 ← default si el campo está ausente o vacío |
| Fecha de inicio | [PENDIENTE] |
| Última actualización | [PENDIENTE] |

**`execution_mode` — valores válidos:**
- `INIT`: bootstrap — activa protocolo de entrevista en `skills/init.md`. No carga ningún módulo de specs/active/ hasta que INIT complete y el usuario confirme.
- `DEVELOPMENT`: produce código funcional y probado. Carga `specs/active/functional.md` + `specs/active/architecture.md`.
- `RESEARCH`: produce informe con hallazgos citados. Carga `specs/active/research.md`.
- `MIXED`: DAG con tareas DEV y RES. Carga `specs/active/functional.md` + `specs/active/research.md` + `specs/active/architecture.md`.

**`compliance_scope` — valores válidos:**
- `FULL`: producto público con datos de usuario o industria regulada → ComplianceAgent activo con protocolo completo.
- `MINIMAL`: herramienta interna o POC con autenticación → ComplianceAgent evalúa solo licencias y credenciales.
- `NONE`: herramienta interna sin datos de usuario → ComplianceAgent no se crea.

---

## Tabla de Módulos y Carga por Agente

| Módulo | Agente que lo carga | Cuándo | Modo activo |
|---|---|---|---|
| `specs/active/functional.md` | Master Orchestrator, AuditAgent, Domain Orchestrators | Inicio de objetivo DEVELOPMENT | DEVELOPMENT, MIXED |
| `specs/active/research.md` | Master Orchestrator, AuditAgent, ResearchOrchestrator | Inicio de objetivo RESEARCH | RESEARCH, MIXED |
| `specs/active/architecture.md` | Master Orchestrator, Domain Orchestrators | Construcción del DAG | DEVELOPMENT, MIXED |
| `specs/active/quality.md` | StandardsAgent, TestWriter | Gate 2 + inicio de tarea de tests | DEVELOPMENT, MIXED |
| `specs/active/security.md` | SecurityAgent | Todos los gates | TODOS |
| `specs/active/compliance.md` | ComplianceAgent, Master Orchestrator | FASE 0 + Gate 3 | TODOS |

---

## Estado del Objetivo Activo

| Atributo | Valor |
|---|---|
| Objetivo en curso | [PENDIENTE] |
| RFs en scope | [PENDIENTE] |
| Estado | PENDIENTE |
| Última ejecución completada | — |
| Commit de entrega | — |

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
| v0.1 | [PENDIENTE] | Inicialización del proyecto |
