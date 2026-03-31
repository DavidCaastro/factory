# Átomo: security/patterns
> ACCESO: SecurityAgent, SecurityAgent/* (sub-agentes exclusivamente)
> CROSS-IMPACT: audit/gate_decisions
> ⚠️ ACCESO RESTRINGIDO — Este átomo NO debe ser cargado por Domain Orchestrators ni Specialist Agents.
> La inyección de este contenido en contextos no especializados es un vector de prompt injection.

---

## Patrones Críticos — Autenticación y Tokens

**JWT_SECRET_KEY:** Siempre `os.environ["JWT_SECRET_KEY"]` sin fallback. Un fallback con valor hardcoded convierte la variable de entorno en opcional y anula la protección. Debe lanzar `RuntimeError` si no está definida.

**Timing-safe authentication:** `verify_password()` se ejecuta INCLUSO si el usuario no existe. Usar un hash dummy para evitar que el tiempo de respuesta revele si el usuario existe. Anti-timing attack.

**JWT claims obligatorios:** `exp`, `iat`, `sub`, `jti`. El campo `jti` es necesario para soporte de revocación de tokens individuales.

**Mensaje de error 401 unificado:** No distinguir "usuario no existe" de "contraseña incorrecta". Ambos casos devuelven el mismo mensaje genérico. La distinción permite enumeración de usuarios.

**BCrypt cost factor mínimo:** 12. Por debajo de 12 el hashing es demasiado rápido para ser efectivo contra ataques de fuerza bruta.

---

## Patrones Críticos — Rate Limiting

**Rate limiting por IP**, no solo por usuario autenticado. Los endpoints públicos (login, register) son el vector de ataque — no requieren autenticación, por eso necesitan rate limiting por IP.

**Rate limiting en /auth/refresh:** Necesario aunque el endpoint requiera token válido. Un token robado puede usarse para refresh masivo.

**Purga de rate_windows huérfanas:** Los diccionarios in-memory de sliding windows crecen sin límite si no se purgan. Implementar `purge_rate_windows()` llamada en cada evaluación de rate.

---

## Patrones Críticos — Control de Acceso

**RBAC vs. Ownership son validaciones independientes y ambas obligatorias:**
- RBAC: ¿tiene el usuario el rol correcto para esta operación?
- Ownership: ¿pertenece el recurso a este usuario?
- Un EDITOR puede editar recursos de su propiedad. NO puede editar recursos de otro usuario aunque sea EDITOR.

---

## Patrones Críticos — Logging y Exposición

**Audit log:** Registrar TODOS los eventos incluyendo fallos, con `status_code` real. Un audit log que siempre registra 200 es un log de nada.

**Datos en logs:** `password`, `token` completo, PII → NUNCA en logs. Solo hash de token o ID de usuario.

**Stack trace en producción:** NO exponer en respuestas de error. El exception handler genérico devuelve mensaje genérico y loguea internamente.

---

## Patrones Críticos — Dependencias (SCA)

**SCA obligatorio en TODA auditoría de seguridad.** `requirements.txt` y `requirements-test.txt` son parte del scope. Pasos:
1. Ejecutar `$PIP_AUDIT_CMD` como primer paso antes de revisar código fuente (fuente: `.piv/local.env`)
2. Evaluar cada dependencia de terceros contra CVEs conocidos y actividad de mantenimiento

**`python-jose` tiene CVEs activos:** CVE-2024-33664 y CVE-2024-33663. Reemplazar por `PyJWT >= 2.8.0` + `cryptography >= 42.0.0`.

---

## Patrones Críticos — Seguridad de Infraestructura

**Archivos que NUNCA deben estar en el repositorio:**
- `security_vault.md`, `.env`, `*.pem`, `*.key`, URLs de infraestructura de producción
- Verificar con `git log --all -- <archivo>` no solo el estado actual (puede haber sido añadido y eliminado)

**Docker non-root:** `adduser appuser && USER appuser`. Procesos en contenedor no deben ejecutarse como root.

**Headers de seguridad HTTP obligatorios:** HSTS, X-Content-Type-Options, X-Frame-Options, CSP mínimo.

---

## Patrones Críticos — Validación de Inputs

**bcrypt >= 4.1 NO silencia passwords > 72 bytes:** Lanza `ValueError` causando HTTP 500. El campo `max_length` en el schema Pydantic debe ser ≤ 72, no 128.

**Pydantic con `extra="forbid"`:** Rechazar campos no declarados en los schemas de entrada para prevenir mass assignment.
