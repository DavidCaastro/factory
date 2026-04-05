# SPECS — Índice de Módulos (Contrato de Ejecución)
> Este archivo es el único que el Master Orchestrator lee en el primer paso de FASE 1.
> A partir de este índice determina qué módulos cargar, para qué agente, y cuándo.
> Escritura: generado con confirmación humana. Inmutable durante ejecución activa.

---

## Identidad del Proyecto

| Atributo | Valor |
|---|---|
| Nombre | SecOps Scanner |
| Versión activa | v0.1 |
| Stack principal | Python 3.11 |
| Mercado objetivo | Interno — framework PIV/OAC y proyectos derivados |
| Tipo de producto | Módulo de análisis de seguridad autónomo (sin LLM) |
| execution_mode | PRODUCTION |
| compliance_scope | MINIMAL |
| gate3_reminder_hours | 24 |
| Fecha de inicio | 2026-04-03 |
| Última actualización | 2026-04-05 |

---

## Tabla de Módulos y Carga por Agente

| Módulo | Agente que lo carga | Cuándo | Modo activo |
|---|---|---|---|
| `specs/active/functional.md` | Master Orchestrator, AuditAgent, Domain Orchestrators | Inicio de objetivo | DEVELOPMENT |
| `specs/active/architecture.md` | Master Orchestrator, Domain Orchestrators | Construcción del DAG | DEVELOPMENT |
| `specs/active/quality.md` | StandardsAgent, TestWriter | Gate 2 + inicio de tarea de tests | DEVELOPMENT |
| `specs/active/security.md` | SecurityAgent | Todos los gates | TODOS |

---

## Estado del Objetivo Activo

| Atributo | Valor |
|---|---|
| Objetivo en curso | Ninguno — sin objetivo activo |
| RFs en scope | — |
| Estado | Sin objetivo activo. Próximo objetivo iniciará desde `skills/init.md` |
| Última ejecución completada | 2026-04-05 (OBJ-006) |
| Commit de entrega | dda47ce (OBJ-006 quality closure → main) |

---

## Contexto de Origen

Este objetivo nació de la necesidad de cubrir vulnerabilidades de dependencias —
incluyendo zero-days y ataques de supply chain — sin depender de herramientas de
terceros ni bases de datos de CVEs. El módulo opera 100% local, sin LLM, sin
agentes, y produce un payload pre-generado que SecurityAgent consume al inicio de
cada sesión sin costo de contexto adicional.

Casos de referencia validados durante diseño:
- CVE-2025-27152 (axios SSRF + credential leakage)
- CVE-2025-58754 (axios DoS via data: URI sin límite de memoria)
- Supply chain attack axios@1.14.1 (RAT inyectado vía cuenta de mantenedor comprometida)

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
| v0.1 | 2026-04-03 | Inicialización — diseño consolidado en sesión con usuario |
| v0.2 | 2026-04-04 | Cierre OBJ-004 — estado actualizado a COMPLETADO, execution_mode→PRODUCTION, evidencias registradas |
| v0.3 | 2026-04-05 | Cierre OBJ-006 — quality closure: 230 tests, 94% cobertura, DoD completa, sin objetivo activo |
