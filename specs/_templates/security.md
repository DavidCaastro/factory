# Especificaciones de Seguridad — [NOMBRE DEL PROYECTO]
> Cargado por: SecurityAgent y SecurityAgent/* (exclusivamente)
> Define los requisitos de seguridad específicos de ESTE producto.
> Los patrones de implementación están en `skills/backend-security.md`.
> Los patrones aprendidos están en `engram/security/patterns.md`.
> ⚠️ ACCESO RESTRINGIDO — igual que engram/security/

---

## Modelo de Amenazas (Threat Model)

| Categoría OWASP | Amenaza | Mitigación requerida | Estado |
|---|---|---|---|
| A01 — Broken Access Control | [amenaza] | [mitigación] | PENDIENTE |
| A02 — Cryptographic Failures | [amenaza] | [mitigación] | PENDIENTE |
| A03 — Injection | [amenaza] | [mitigación] | PENDIENTE |
| A04 — Insecure Design | [amenaza] | [mitigación] | PENDIENTE |
| A05 — Security Misconfiguration | [amenaza] | [mitigación] | PENDIENTE |
| A07 — Auth Failures | [amenaza] | [mitigación] | PENDIENTE |
| A09 — Logging Failures | [amenaza] | [mitigación] | PENDIENTE |

> Completar durante FASE 1. SecurityAgent revisa y valida en cada gate.
> Referencia de patrones: `engram/security/patterns.md`

---

## Requisitos de Seguridad del Producto

### Autenticación
- [PENDIENTE — definir mecanismo de autenticación y requisitos específicos]

### Gestión de Secretos
- Ninguna credencial en código fuente ni en logs
- Variables de entorno sensibles sin fallback con valor por defecto
- `.env` en `.gitignore`
- `security_vault.md` en `.gitignore`

### Autorización
- [PENDIENTE — definir modelo de autorización (RBAC, ABAC, etc.)]

### Headers de Seguridad HTTP
- [PENDIENTE — definir headers requeridos según el tipo de producto]

### Audit Log
- [PENDIENTE — definir eventos a registrar y campos requeridos]

---

## Dependencias de Seguridad

| Dependencia | Versión requerida | Razón |
|---|---|---|
| [PENDIENTE] | [PENDIENTE] | [PENDIENTE] |

> Ejecutar `pip-audit` antes de Gate 2. Resultado: 0 vulnerabilidades.

---

## Limitaciones de Seguridad Conocidas

| Limitación | Impacto | Resolución en producción |
|---|---|---|
| [PENDIENTE — documentar limitaciones conocidas del POC o versión actual] | — | — |
