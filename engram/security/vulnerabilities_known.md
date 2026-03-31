# Átomo: security/vulnerabilities_known
> ACCESO: SecurityAgent, SecurityAgent/* (sub-agentes exclusivamente)
> CROSS-IMPACT: audit/gate_decisions
> ⚠️ ACCESO RESTRINGIDO — Solo SecurityAgent y sus sub-agentes.
> Historial de vulnerabilidades detectadas y su estado de resolución.

---

## Vulnerabilidades Resueltas — auth-service (2026-03-13)

| ID | Severidad | Descripción | Fix aplicado |
|---|---|---|---|
| VULN-001 | CRÍTICA | JWT_SECRET_KEY con fallback a valor hardcoded | `os.environ["JWT_SECRET_KEY"]` sin fallback |
| VULN-007 | ALTA | Sin rate limiting por IP en /auth/login | Rate limiting 10 req/15min, sliding window |
| VULN-016 | ALTA | PUT /resources/{id} no verifica ownership | Validación `owner_id == current_user.sub` |
| VULN-005 | ALTA | Sin purga de tokens revocados expirados | `purge_expired_tokens()` en cada `is_token_revoked()` |
| VULN-023 | ALTA | security_vault.md no en .gitignore | Añadido a .gitignore |
| VULN-004 | MEDIA | Sin security headers HTTP | Security headers middleware |
| VULN-012 | MEDIA | Intentos fallidos de login no auditados | Registro con `event: login_failed` |
| VULN-015 | MEDIA | Logout no revoca refresh token | Acepta `refresh_token` opcional y revoca ambos |
| VULN-014 | BAJA | JWT sin claim `iat` | Añadido `iat` en `_create_token()` |

## Vulnerabilidades No Resueltas (limitaciones estructurales del POC)

| ID | Razón | Mitigación recomendada para producción |
|---|---|---|
| VULN-021 | In-memory pierde estado al reiniciar | Usar base de datos persistente |
| VULN-009/010 | Race conditions sin locks | Usar base de datos con transacciones |
| VULN-022 | Audit log mutable | Sistema de logs externo inmutable (append-only) |
| VULN-003 | CORS no configurado | Configurar con dominios de producción conocidos |
| VULN-032 | Prompt injection en templates de invocación | Mejora estructural de prompts del framework pendiente |

## Dependencias Vulnerables Identificadas

| Dependencia | CVEs | Reemplazo |
|---|---|---|
| python-jose[cryptography]>=3.3.0 | CVE-2024-33664, CVE-2024-33663 | PyJWT>=2.8.0 + cryptography>=42.0.0 |

---

## Lección: Gap de SCA en protocolo (2026-03-13)

**Causa raíz del gap:** El SecurityAgent analizó solo archivos `src/`. `requirements.txt` no estaba en el scope inicial. La dependencia vulnerable `python-jose` pasó el primer gate sin ser detectada.

**Regla operativa resultante:** `requirements.txt` y `requirements-test.txt` son parte obligatoria del scope de TODA auditoría. `pip audit` es el primer paso, antes de revisar código fuente.
