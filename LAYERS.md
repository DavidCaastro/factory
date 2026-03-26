# LAYERS.md — Contrato de Separación de Capas PIV/OAC

> Este documento define las tres capas del framework PIV/OAC y las reglas que determinan a qué capa pertenece cada artefacto.
> **Scope:** Separación de capas del FRAMEWORK (quién gestiona qué en el sistema PIV/OAC).
> **Distinto de** `skills/layered-architecture.md`, que define arquitectura por capas del PRODUCTO (Transport/Domain/Data del software construido).

---

## CAPA 1 — FRAMEWORK

**Definición:** Artefactos universales del framework PIV/OAC. Viajan intactos entre proyectos y repositorios. Son inmutables durante la ejecución de un objetivo.

**Responsable:** Master Orchestrator + StandardsAgent (inmutabilidad durante ejecución).
Solo pueden modificarse mediante el ciclo completo: StandardsAgent propone → SecurityAgent revisa → confirmación humana explícita.

**Artefactos:**

| Artefacto | Descripción |
|---|---|
| `CLAUDE.md` | Entrypoint operativo del framework |
| `agent.md` | Marco operativo PIV/OAC completo |
| `LAYERS.md` | Este archivo — contrato de separación de capas |
| `LICENSE` | Licencia de distribución del framework |
| `contracts/` | Primitivas canónicas compartidas — cargables independientemente por agente |
| `contracts/gates.md` | Fuente única de Gate 1, 2, 2b, 3 (checklists + criterios) |
| `contracts/models.md` | Tabla de asignación de modelos por agente |
| `contracts/evaluation.md` | Rubric de scoring 0-1 + resource policy + schema JSONL |
| `contracts/parallel_safety.md` | Reglas de aislamiento para grupos paralelos |
| `registry/` | Catálogo de agentes, protocolos y gates |
| `skills/` | Skills de carga perezosa por agente |
| `engram/core/` | Decisiones de arquitectura y patrones operativos (Master Orchestrator) |
| `engram/security/` | Patrones de ataque y vulnerabilidades conocidas (SecurityAgent exclusivo) |
| `engram/quality/` | Patrones de código y testing (StandardsAgent) |
| `engram/coherence/` | Patrones de conflictos entre expertos (CoherenceAgent) |
| `engram/compliance/` | Patrones de riesgo legal/ético (ComplianceAgent) |
| `engram/audit/` | Historial de gates y cobertura de RF (AuditAgent) |
| `metrics/schema.md` | Esquema de métricas y protocolo de interpretación |
| `.piv/README.md` | Documentación del sistema de estado PIV |

**Política de lazy loading para `contracts/`:** Cada archivo en `contracts/` es cargable independientemente. Los agentes cargan SOLO el contrato relevante a su tarea (no `contracts/` completo). Ejemplos: CoherenceAgent carga `contracts/gates.md §Gate 1` + `contracts/evaluation.md`; EvaluationAgent carga solo `contracts/evaluation.md`; Domain Orchestrators cargan `contracts/models.md` para asignación de modelos de expertos.

**Nunca pertenece aquí:**
- `specs/` con valores de proyecto específico
- Logs de sesión específicos (`logs_veracidad/`, `metrics/sessions.md`)
- Artefactos de runtime (`gates/`, `worktrees/`, `.piv/active/`)
- Knowledge de dominio de proyecto (`engram/domains/`)

---

## CAPA 2 — PROYECTO

**Definición:** Artefactos particulares por repositorio o proyecto. Cambian entre proyectos pero sobreviven entre sesiones del mismo proyecto.

**Responsable:** Usuario + Master Orchestrator (con confirmación humana explícita para cambios en `specs/`).

**Artefactos:**

| Artefacto | Descripción |
|---|---|
| `specs/INDEX.md` | Identidad del proyecto, versión, tabla de módulos, execution_mode |
| `specs/functional.md` | Requisitos funcionales con criterios de aceptación |
| `specs/architecture.md` | Stack, DAG, estructura de módulos del producto |
| `specs/quality.md` | NFRs: cobertura, linting, Definition of Done |
| `specs/security.md` | Requisitos de seguridad del producto |
| `specs/compliance.md` | Perfil legal, licencias, GDPR checklist |
| `metrics/sessions.md` | Registro histórico de sesiones (generado por AuditAgent en FASE 8) |
| `compliance/<objetivo>/` | Informes y paquetes de entrega por objetivo |
| `engram/domains/` | Knowledge específico por dominio de proyecto |

**Nunca pertenece aquí:**
- Archivos del framework (`registry/`, `skills/`, `agent.md`, `CLAUDE.md`)
- Artefactos de runtime generados durante ejecución (`gates/`, `worktrees/`)
- Credenciales o secretos (van a `security_vault.md` bajo Zero-Trust)

---

## CAPA 3 — RUNTIME ARTIFACTS

**Definición:** Artefactos generados durante la ejecución de un objetivo. Son temporales y no necesitan persistir entre sesiones.

**Responsable:** Domain Orchestrators durante ejecución. Se generan solo tras aprobación de gate de entorno de control.

**Artefactos:**

| Artefacto | Descripción |
|---|---|
| `gates/` | Evidencias de aprobación de gates (Gate 1, 2, 3) |
| `worktrees/` | Subramas de trabajo de expertos (nunca versionadas) |
| `logs_veracidad/` | Logs generados por AuditAgent al cierre de sesión |
| `.piv/active/` | Estado de sesiones en curso |
| `.piv/completed/` | Estado de sesiones completadas |
| `.piv/failed/` | Estado de sesiones fallidas |

**Excepción notable:** `logs_veracidad/intent_rejections.jsonl` SÍ se versiona (registro de vetos de intención — relevante para auditoría permanente).

**Nunca pertenece aquí:**
- `specs/` (contratos de proyecto — sobreviven entre sesiones)
- Archivos del framework (`registry/`, `skills/`)
- Knowledge engram de dominio

---

## Regla de Precedencia

Si un artefacto califica para múltiples capas, aplicar en orden:

```
1. Si es inmutable entre proyectos → FRAMEWORK (Capa 1)
2. Si cambia por proyecto pero sobrevive entre sesiones → PROYECTO (Capa 2)
3. Si se genera durante ejecución y no necesita persistir entre sesiones → RUNTIME (Capa 3)
```

**Ejemplos de aplicación:**

| Artefacto | Razonamiento | Capa |
|---|---|---|
| `skills/testing.md` | Inmutable entre proyectos, definido por el framework | FRAMEWORK |
| `specs/functional.md` | Cambia por proyecto, sobrevive entre sesiones | PROYECTO |
| `worktrees/task-01/` | Generado durante ejecución, no persiste | RUNTIME |
| `metrics/schema.md` | Inmutable entre proyectos (define formato, no datos) | FRAMEWORK |
| `metrics/sessions.md` | Cambia por proyecto (datos históricos de sesiones) | PROYECTO |
| `logs_veracidad/intent_rejections.jsonl` | Excepción: runtime con versionado explícito | RUNTIME* |

---

## Nota de Scope

| Documento | Scope |
|---|---|
| **LAYERS.md** (este archivo) | Separación de capas del **FRAMEWORK** — qué gestiona qué en el sistema PIV/OAC |
| **`skills/layered-architecture.md`** | Arquitectura por capas del **PRODUCTO** — Transport/Domain/Data del software construido |

Ambos son complementarios y abordan scopes completamente distintos.
