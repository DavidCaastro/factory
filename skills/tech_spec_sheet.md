# SKILL: Technical Specification Sheet (TechSpecSheet) — PIV/OAC v3.2
> Cargado por: AuditAgent en FASE 8 para generar el TechSpecSheet del objetivo
> Estándares de referencia:
>   - ISO/IEC/IEEE 29148:2018 — Trazabilidad y verificabilidad de requisitos
>   - ISO/IEC 25010:2023 — Modelo de calidad del producto software (revisión Product Quality)
>   - OpenAPI Specification 3.1 — Para productos que exponen APIs REST
>
> REGLA CRÍTICA: Todo valor numérico o de estado en el TechSpecSheet debe provenir
> de una fuente verificable (herramienta ejecutada, gate report, git log).
> Ningún valor puede ser estimado o inferido. Si una métrica no puede medirse → registrar N/D + razón.

---

## Plantilla de TechSpecSheet

El AuditAgent genera el archivo en:
`/compliance/<objetivo>/delivery/TECH_SPEC_SHEET.md`

Sustituir todos los campos `[...]` con valores reales de las fuentes indicadas.

---

```markdown
# Technical Specification Sheet
**Producto:** [nombre del producto — de project_spec.md]
**Objetivo:** [nombre del objetivo — de la tarea completada]
**Generado por:** AuditAgent — PIV/OAC v3.2
**Fecha de generación:** [YYYY-MM-DD]
**Commit de entrega (main):** [hash completo — de git log]
**Rama de framework:** [rama agent-configs activa — de git log]

> Estándares aplicados: ISO/IEC/IEEE 29148:2018 | ISO/IEC 25010:2023
> DISCLAIMER: Los valores de métricas provienen de herramientas ejecutadas. La sección de
> compliance no constituye asesoramiento legal. Ver /compliance/<objetivo>_compliance.md.

---

## I. IDENTIDAD

| Atributo | Marco (Directive) | Producto (Artifact) |
|---|---|---|
| Nombre | PIV/OAC | [nombre del producto] |
| Versión | v3.2 | [versión semántica del producto] |
| Fecha de entrega | [fecha] | [fecha] |
| Commit | [hash corto — agent-configs] | [hash corto — main] |
| Rama de entrega | agent-configs | main |
| Autor/Equipo | [usuario] | [usuario] |

**Fuente:** `git log --oneline -1` en cada rama.

---

## II. REQUISITOS FUNCIONALES (ISO/IEC/IEEE 29148:2018)

> Un requisito se considera CUMPLIDO solo si tiene evidencia de archivo:línea verificable.

| RF-ID | Descripción | Estado | Evidencia | Versión introducida |
|---|---|---|---|---|
| RF-01 | [descripción del RF — de project_spec.md] | CUMPLIDO / PARCIAL / PENDIENTE | [archivo:línea] | v[N] |

**Fuente:** `verificacion_intentos.txt` generado por AuditAgent. Sin este archivo → sección no puede completarse.

---

## III. ATRIBUTOS DE CALIDAD (ISO/IEC 25010:2023 — Product Quality)

| Característica | Sub-característica | Marco (Directive) | Producto (Artifact) | Medición |
|---|---|---|---|---|
| **Seguridad** | Confidencialidad | Zero-Trust + MCP para secretos | JWT (HS256/RS256) + variables de entorno sin fallback | Gate SecurityAgent: [N/N aprobados] |
| **Seguridad** | Integridad | Logs append-only + SHA-256 | RBAC + ownership validation | Checklist OWASP: [N/N ítems OK] |
| **Seguridad** | Autenticidad | SecurityAgent veto pre-código | BCrypt cost ≥12 + timing-safe verify | SCA: [0 CVEs / N CVEs] |
| **Fiabilidad** | Madurez | Gates de control: [N/N aprobados] | Tests passing: [N/N] | Cobertura: [N]% |
| **Fiabilidad** | Tolerancia a fallos | Protocolo escalado (3 intentos → orquestador) | Exception handler genérico + HTTP 500 sin stack trace | [PASS/FAIL] |
| **Mantenibilidad** | Modularidad | Agentes atómicos + /skills/ + /registry/ | Arquitectura por capas (Transport→Domain→Data) | Complejidad ciclomática media: [N] |
| **Mantenibilidad** | Testeabilidad | Gates pre-código bloqueantes | pytest + httpx + conftest fixtures | Cobertura: [N]% |
| **Mantenibilidad** | Modificabilidad | /skills/ inmutables salvo gate + humano | [patrón de extensibilidad del producto] | Linting: [0 / N errores ruff] |
| **Eficiencia** | Uso de recursos | Lazy Loading + OAC (tokens mínimos) | [métricas de memoria/CPU si aplica] | Tokens por sesión: [N estimado] |
| **Compatibilidad** | Interoperabilidad | MCP para secretos, git para versionado | OpenAPI [versión] / REST | [PASS/FAIL — OpenAPI válido] |
| **Portabilidad** | Instalabilidad | Claude API + entorno bash | Docker + [requirements.txt / pyproject.toml] | Docker build: [PASS/FAIL] |

**Fuente por columna:**
- Marco: registros de gates en `logs_veracidad/acciones_realizadas.txt`
- Producto: outputs de pytest-cov, ruff, pip-audit, Docker build
- Medición: herramientas ejecutadas (no estimadas)

---

## IV. MÉTRICAS DE PRODUCCIÓN

| Métrica | Valor medido | Herramienta | Umbral requerido | Estado |
|---|---|---|---|---|
| Cobertura total de tests | [N]% | pytest-cov | ≥90% (CI gate) | PASS / FAIL |
| Cobertura flujos críticos | [N]% | pytest-cov | 100% | PASS / FAIL |
| Tests passing | [N]/[N] | pytest | 100% | PASS / FAIL |
| Errores de linting | [N] | ruff | 0 | PASS / FAIL |
| Vulnerabilidades en dependencias | [N] | pip-audit | 0 | PASS / FAIL |
| Complejidad ciclomática máxima | [N] | radon / ruff | ≤10 | PASS / FAIL |
| Gates de framework aprobados | [N]/[N] | PIV/OAC | 100% | PASS / FAIL |
| Gates rechazados (iteraciones) | [N] | AuditAgent logs | — | INFO |

**Fuente:** Outputs directos de herramientas. Si pytest-cov no se ejecutó → FAIL por defecto.

---

## V. POSTURA DE SEGURIDAD

| Dimensión | Marco (Directive) | Producto (Artifact) |
|---|---|---|
| Modelo de seguridad | Zero-Trust metodológico + SecurityAgent Opus | [modelo de seguridad del producto] |
| Gestión de secretos | MCP + security_vault.md (Zero-Trust) | Variables de entorno (`os.environ[...]` sin fallback) |
| Autenticación | N/A (framework) | [mecanismo: JWT / OAuth2 / API Key] |
| Autorización | Gate SecurityAgent pre-código | [RBAC / ABAC / etc.] |
| Auditoría | logs_veracidad/ append-only + SHA-256 | [mecanismo de audit log del producto] |
| Checklists completados | OWASP Top 10 (framework) | [lista de checklists de skills/compliance.md] |
| CVEs conocidos irresueltos | [N — ref: engram/security/vulnerabilities_known.md] | [N — ref: pip-audit output] |
| Riesgos no resolubles con código | [ref: Documento de Mitigación o NINGUNO] | [ídem] |

**Fuente:** Gate 2b de SecurityAgent + ComplianceAgent Gate 3 + pip-audit.

---

## VI. COMPLIANCE LEGAL

| Estándar / Regulación | Aplicabilidad | Estado | Referencia |
|---|---|---|---|
| GDPR (Reglamento UE 2016/679) | [SÍ/NO — si maneja datos UE] | [CHECKLIST OK / PENDIENTE REVISIÓN LEGAL] | compliance/<objetivo>_compliance.md |
| OWASP API Security Top 10 | [SÍ/NO — si expone API] | [N/N ítems OK] | skills/compliance.md |
| Licencias de dependencias | SÍ | [COMPATIBLE / CONFLICTO DETECTADO] | compliance/<objetivo>/delivery/LICENSES.md |
| [Otros según producto] | [SÍ/NO] | [estado] | — |

**Fuente:** ComplianceAgent Gate 3 report + `/compliance/<objetivo>_compliance.md`.

---

## VII. INFRAESTRUCTURA Y DESPLIEGUE

| Aspecto | Marco (Directive) | Producto (Artifact) |
|---|---|---|
| Modelo de ejecución | Agentes LLM via Claude API | [runtime: Python 3.11 / Node / etc.] |
| Requisitos de entorno | Claude API key + MCP + bash | [variables de entorno requeridas — de .env.example] |
| Containerización | N/A | [Docker image + tag / N/A] |
| CI/CD | GitHub Actions (agent-configs) | [pipeline del producto] |
| Estrategia de rollback | `git revert [hash]` | [estrategia de rollback del producto] |
| Entorno de despliegue objetivo | N/A | [cloud provider / on-premise / etc.] |

**Fuente:** project_spec.md + Dockerfile + .github/workflows/ + .env.example.

---

## VIII. DEPENDENCIAS CRÍTICAS

| Dependencia | Versión mínima | Licencia | CVEs activos | Alternativa verificada |
|---|---|---|---|---|
| [nombre] | [versión] | [licencia] | [0 / lista CVEs] | [alternativa o N/A] |

**Fuente:** requirements.txt (o pyproject.toml) + pip-audit output. Todas las filas deben completarse antes del merge a main.

---

## IX. FUENTES DE DATOS DEL SHEET

> Esta sección documenta de dónde viene cada dato. Un TechSpecSheet sin fuentes verificables no es válido.

| Sección | Fuente primaria | Agente responsable | Modo de obtención |
|---|---|---|---|
| I — Identidad | `git log` | AuditAgent | Ejecutado |
| II — RFs | `verificacion_intentos.txt` + project_spec.md | AuditAgent | Archivo generado por AuditAgent |
| III — Calidad (columna Marco) | `logs_veracidad/acciones_realizadas.txt` | AuditAgent | Archivo append-only |
| III — Calidad (columna Producto) | pytest-cov + ruff + pip-audit | StandardsAgent → AuditAgent | Herramientas ejecutadas |
| IV — Métricas | pytest-cov + ruff + pip-audit outputs | StandardsAgent → AuditAgent | Herramientas ejecutadas |
| V — Seguridad | Gate 2b SecurityAgent + acciones_realizadas.txt | SecurityAgent → AuditAgent | Gate report |
| VI — Compliance | Gate 3 ComplianceAgent + compliance_report | ComplianceAgent → AuditAgent | Informe generado |
| VII — Infraestructura | project_spec.md + Dockerfile + .env.example | AuditAgent | Lectura directa |
| VIII — Dependencias | requirements.txt + pip-audit | SecurityAgent/crypto → AuditAgent | Herramientas ejecutadas |

---

*Generado por PIV/OAC v3.2 — AuditAgent*
*DISCLAIMER: Los valores numéricos provienen de herramientas ejecutadas, no de estimaciones.
La sección de compliance es una referencia técnica y no constituye asesoramiento legal.*
```

---

## Reglas de generación para el AuditAgent

1. **Orden de recolección de datos (secuencial, FASE 8):**
   - Primero: recolectar outputs de herramientas (pytest-cov, ruff, pip-audit) del StandardsAgent y SecurityAgent
   - Luego: recolectar gate reports del entorno de control
   - Finalmente: completar el sheet y guardarlo en `/compliance/<objetivo>/delivery/TECH_SPEC_SHEET.md`

2. **Valores N/D:** Si una métrica no puede obtenerse de herramienta ejecutada, registrar `N/D (razón)`. Nunca dejar un campo vacío ni estimarlo.

3. **El sheet es append-only desde la perspectiva del historial:** Si el objetivo tiene una versión anterior, crear un nuevo archivo con versión en el nombre (`TECH_SPEC_SHEET_v2.md`), no sobreescribir el anterior.

4. **El sheet no reemplaza los logs de veracidad:** Es un resumen ejecutivo para entrega. Los logs de `logs_veracidad/` son el registro técnico detallado.
