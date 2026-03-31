# Especificaciones de Calidad — PIV/OAC SDK v4.0
> Cargado por: StandardsAgent (Gate 2b), TestWriter (inicio de tarea de tests)
> ISO/IEC 25010:2023 — Non-Functional Requirements del producto

---

## Umbrales de Cobertura de Tests

| Tipo de módulo | Umbral requerido | Herramienta | Estado actual |
|---|---|---|---|
| `core/` — AgentFactory, GateEnforcer, CryptoValidator, CSP, PermissionStore | 100% líneas + ramas | pytest-cov | PENDIENTE |
| `core/memory/` — AtomLoader (Code Signing es crítico para seguridad) | 100% líneas + ramas | pytest-cov | PENDIENTE |
| `agents/logistics.py` — caps de estimación (defensa DoW) | 100% líneas + ramas | pytest-cov | PENDIENTE |
| `agents/execution_auditor.py` | ≥ 95% | pytest-cov | PENDIENTE |
| `state/` — StateStore, FilesystemStateStore, RedisStateStore | ≥ 90% | pytest-cov | PENDIENTE |
| `recovery/` — RollbackManager | ≥ 90% | pytest-cov | PENDIENTE |
| `providers/` — ProviderRegistry | ≥ 85% | pytest-cov | PENDIENTE |
| `observability/` — RealtimeMetrics, Telemetry | ≥ 85% | pytest-cov | PENDIENTE |
| Coverage gate global en CI | ≥ 90% | `--cov-fail-under=90` | PENDIENTE |

> Los módulos `core/` y `core/memory/` exigen 100% porque implementan controles de seguridad
> (gate enforcement, HMAC, Code Signing). Un branch sin cubrir puede ser un bypass no detectado.

---

## Requisitos de Calidad de Código

| Métrica | Umbral | Herramienta | Estado actual |
|---|---|---|---|
| Errores de linting | 0 | ruff | PENDIENTE |
| Vulnerabilidades en dependencias | 0 CVEs críticos/altos | pip-audit | PENDIENTE |
| Type checking (módulos core/) | 0 errores en strict mode | mypy --strict | PENDIENTE |
| Type checking (resto) | 0 errores en modo normal | mypy | PENDIENTE |
| Complejidad ciclomática | ≤ 10 por función | radon (si disponible) | PENDIENTE |
| Longitud máxima de función | 60 líneas (sin docstring) | revisión manual | PENDIENTE |
| Secretos en código | 0 | grep (patterns del protocolo) | PENDIENTE |

---

## Requisitos de Documentación

| Elemento | Requisito | Estado actual |
|---|---|---|
| Clases públicas de `core/` | Docstring con descripción, responsabilidad, restricciones de uso | PENDIENTE |
| Métodos públicos de `core/` | Docstring con Args, Returns, Raises | PENDIENTE |
| `AgentFactory.create_agent()` | Docstring con los 5 pasos de instanciación + ejemplo de uso | PENDIENTE |
| `CryptoValidator` | Docstring con política de errores (MessageTampered vs MessageExpired) | PENDIENTE |
| `AtomLoader` | Docstring con protocolo de verificación SHA-256 y condiciones de bloqueo | PENDIENTE |
| `piv_oac.yaml` | Cada sección comentada con descripción y valores válidos | PENDIENTE |
| `skills/manifest.json` | Schema documentado en `README` de la carpeta skills/ | PENDIENTE |
| Variables de entorno | `ANTHROPIC_API_KEY`, `REDIS_URL`, `OTEL_ENDPOINT` documentadas en `.env.example` | PENDIENTE |
| `SECURITY.md` | Política de seguridad del SDK en raíz del proyecto | PENDIENTE |

---

## Requisitos de Tests por RF

Los tests deben cubrir **exactamente** los criterios de aceptación de cada RF en `functional.md`.
No se acepta un gate aprobado si algún criterio de aceptación no tiene test correspondiente.

| RF | Test obligatorio mínimo | Tipo |
|---|---|---|
| RF-FACTORY-01 | Instanciación directa fuera de factory → `InstantiationError` | Unit |
| RF-PERMS-02 | `grant("gate:*:bypass")` → `PermissionDenied` | Unit |
| RF-CRYPTO-01 | Firma alterada → `MessageTampered`, timestamp expirado → `MessageExpired` | Unit |
| RF-CRYPTO-02 | 3 expirados consecutivos → `MessageExpired` propagada | Unit |
| RF-GATE-01 | Gate con 3 agentes, 1 rechaza → `approved=False` + persistido en StateStore | Unit |
| RF-CSP-01 | Diff 1000 líneas → scope SecurityAgent retorna < 1000 líneas | Unit |
| RF-CSP-02 | Sin matches de scope → artefacto completo con prefijo `[CSP: sin matches` | Unit |
| RF-LOGIS-02 | Estimación raw > cap → `estimated_tokens == cap`, `capped = True` | Unit |
| RF-AUDIT-02 | Fallo interno en report → `generate_final_report()` no propaga excepción | Unit |
| RF-STATE-01 | Sin `REDIS_URL` → `FilesystemStateStore` instanciado | Unit |
| RF-SKILLS-01 | Hash modificado en disk → `SkillIntegrityError` | Unit |
| RF-SKILLS-02 | `register_skill()` sin permiso `skill:write` → `PermissionDenied` | Unit |
| RF-ROLL-01 | `auto_rollback(SECURITY_VIOLATION)` → nivel TASK, `user_notified=True` | Unit |
| Test integración | Flujo completo: Factory → Gate 2b con CSP → StateStore → veredicto firmado | Integration |

---

## Métricas de Eficiencia v4.0

| Métrica | Campo | Fórmula / Descripción | Objetivo |
|---|---|---|---|
| token_efficiency_pct | `token_efficiency_pct` | (tokens_actual / tokens_estimated) × 100 | ≤ 120% |
| CSP filter rate por gate | `csp_filter_pct_by_gate` | % del artefacto filtrado por CSP en cada gate | ≥ 25% reducción vs sin CSP |
| Gate compliance rate | `gate_compliance_rate` | % de gates ejecutados sin irregularidades | 100% |
| PMIA retry rate | `pmia_retry_rate` | % de mensajes PMIA que requirieron retry | ≤ 5% |
| Context saturation events | `context_saturation_events` | Número de VETO_SATURACION emitidos | 0 por sesión |

> Las métricas de eficiencia v4.0 son capturadas por RealtimeMetrics y consolidadas en el ExecutionAuditReport.
> Ver schema completo en `metrics/execution_audit_schema.md`.

---

## Definición de Hecho (Definition of Done)

Un objetivo se considera COMPLETADO solo cuando:

1. Todos los RFs en `functional.md` están en estado CUMPLIDO con evidencia de archivo:línea
2. Cobertura global ≥ 90% verificada por pytest-cov (no estimada)
3. Cobertura de módulos `core/` y `core/memory/` al 100% verificada
4. mypy --strict en `core/`: 0 errores
5. ruff: 0 errores
6. pip-audit: 0 CVEs críticos/altos
7. Todos los gates del framework aprobados (Security + Audit + Standards + Coherence)
8. `skills/manifest.json` generado con hashes de todos los skills usados en el objetivo
9. TechSpecSheet generado en `/compliance/<objetivo>/delivery/`
10. Merge a `main` con confirmación humana explícita
