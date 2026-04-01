# SKILL: Backend Security — FastAPI + JWT + BCrypt
> Skill de carga perezosa. Cargar SOLO cuando la tarea involucre autenticación, autorización o seguridad de endpoints.

## Contexto de Aplicación
- **Stack de referencia:** Python 3.10+ · FastAPI · PyJWT · BCrypt
- **Aplicabilidad:** Cualquier proyecto con autenticación JWT + hashing de contraseñas + endpoints REST protegidos
- **RF cubiertos:** Los RFs de autenticación y autorización definidos en `specs/active/functional.md` del proyecto activo
- **Arquitectura:** Capas — Transporte → Dominio → Datos (ver `skills/layered-architecture.md`)
- **Nota:** Este skill es una implementación de referencia para el stack Python/FastAPI. Para otros stacks, adaptar los patrones manteniendo los principios de seguridad.

---

## Patrón 1: Estructura de Capas

> Estructura de carpetas, reglas de importación y patrones de implementación por capa en `skills/layered-architecture.md`.

Resumen: `transport/` → `domain/` → `data/`. Flujo unidireccional estricto. Nunca al revés.

---

## Patrón 2: Hashing de Contraseñas con BCrypt

```python
# domain/auth_service.py
import bcrypt

def hash_password(plain_password: str) -> str:
    """Genera hash BCrypt con salt automático (cost factor 12)."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Comparación timing-safe. Nunca comparar strings directamente."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )
```

**Reglas de seguridad:**
- Nunca almacenar contraseñas en texto plano.
- Nunca loguear `plain_password` bajo ninguna circunstancia.
- Cost factor mínimo: 12 (ajustar según benchmark de hardware en producción).

---

## Patrón 3: Generación y Validación de JWT

```python
# domain/auth_service.py
import jwt
from datetime import datetime, timedelta, timezone

# La clave secreta llega SIEMPRE desde MCP o variable de entorno. Nunca hardcodeada.
def create_access_token(subject: str, secret_key: str, expires_delta_hours: int = 1) -> str:
    """Genera JWT firmado HS256 con expiración."""
    payload = {
        "sub": subject,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=expires_delta_hours),
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")

def decode_access_token(token: str, secret_key: str) -> dict:
    """Valida firma y expiración. Lanza excepción si el token es inválido."""
    return jwt.decode(token, secret_key, algorithms=["HS256"])
```

---

## Patrón 4: Caché de Tokens con Dict (Hashmap)

Para invalidación de tokens (logout, revocación) se usa un **dict** en memoria:

```python
# domain/token_cache.py

# DECISIÓN DE ESTRUCTURA: Dict (Hashmap) — O(1) por clave
# Justificación: La operación crítica es lookup por token ID (jti).
# Un dict garantiza O(1) para insert, lookup y delete por clave string.
# Un array/lista sería O(n) para búsqueda por valor — inaceptable en producción.

_revoked_tokens: dict[str, datetime] = {}

def revoke_token(jti: str, expires_at: datetime) -> None:
    _revoked_tokens[jti] = expires_at

def is_token_revoked(jti: str) -> bool:
    return jti in _revoked_tokens

def purge_expired(now: datetime) -> None:
    """Limpieza periódica para evitar crecimiento ilimitado."""
    expired = [jti for jti, exp in _revoked_tokens.items() if exp < now]
    for jti in expired:
        del _revoked_tokens[jti]
```

**Nota:** En producción, reemplazar el dict en memoria por Redis vía MCP para persistencia distribuida.

---

## Patrón 5: Endpoint POST /login (Capa Transporte)

```python
# transport/auth_router.py
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

router = APIRouter()

class LoginRequest(BaseModel):
    email: EmailStr
    # CRÍTICO: bcrypt>=4.1 lanza ValueError (→ HTTP 500) para passwords >72 bytes.
    # max_length DEBE ser ≤ 72. No usar 128 aunque el objetivo sea limitar payloads.
    password: str = Field(..., min_length=1, max_length=72)

    model_config = {"extra": "forbid"}

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, auth_service=Depends(get_auth_service)):
    token = await auth_service.authenticate(body.email, body.password)
    if not token:
        # RF-04: Mensaje genérico — no revelar si el fallo fue email o contraseña
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=token)
```

---

## Patrón 6: Sanitización de Errores (RF-04)

**Regla:** Los errores de autenticación NUNCA deben distinguir entre "usuario no existe" y "contraseña incorrecta". Siempre retornar el mismo mensaje genérico y el mismo HTTP 401.

```python
# INCORRECTO — revela información:
# raise HTTPException(404, "Usuario no encontrado")
# raise HTTPException(401, "Contraseña incorrecta")

# CORRECTO — mensaje unificado:
# raise HTTPException(401, "Credenciales inválidas.")
```

**Timing attacks:** Siempre ejecutar `verify_password` incluso si el usuario no existe (comparar contra hash ficticio) para evitar diferencias de tiempo medibles.

---

## Dependencias Requeridas

```txt
fastapi>=0.111.0
uvicorn>=0.29.0
PyJWT>=2.8.0                        # JWT — mantenimiento activo, respuesta rápida a CVEs
cryptography>=42.0.0                # Backend criptográfico para PyJWT
bcrypt>=4.1.0                       # Hashing
pydantic[email]>=2.7.0              # Validación
```

> **NOTA:** `python-jose` está desaconsejada. Tiene CVEs activos (CVE-2024-33664, CVE-2024-33663)
> relacionados con algorithm confusion y `alg: none` bypass. Usar **PyJWT >= 2.8.0** como reemplazo.
> Diferencia de API: `PyJWT` usa `jwt.encode()` / `jwt.decode()` con el mismo contrato,
> pero lanza `jwt.ExpiredSignatureError`, `jwt.InvalidTokenError` en lugar de las excepciones de `jose`.

---

## Patrón 7 — RBAC (Role-Based Access Control)

**Principio:** RBAC verifica autorización, no identidad. Siempre después de autenticación en el middleware chain.

**Matriz de permisos centralizada (constante, no lógica distribuida):**
```python
PERMISSION_MATRIX: dict[str, dict[str, list[str]]] = {
    "GET /resources":       ["VIEWER", "EDITOR", "ADMIN"],
    "POST /resources":      ["EDITOR", "ADMIN"],
    "PUT /resources/{id}":  ["EDITOR", "ADMIN"],
    "DELETE /resources/{id}": ["ADMIN"],
    "GET /admin/audit-log": ["ADMIN"],
}
```

**Ownership validation obligatoria en escritura:**
```python
# RBAC verifica rol, pero NO ownership. Ownership es validación adicional obligatoria.
if user.role != "ADMIN" and resource["owner_id"] != user.sub:
    raise HTTPException(status_code=403, detail="Permisos insuficientes.")
```

**Orden correcto del middleware:** `auth → RBAC → rate_limit`
SecurityAgent DEBE rechazar cualquier plan donde este orden no esté explícito.

**Checklist RBAC:**
- [ ] Matriz de permisos es una constante centralizada
- [ ] Ownership validado en todas las operaciones de escritura (PUT, DELETE)
- [ ] RBAC aplicado DESPUÉS de auth en el middleware chain
- [ ] 403 para permisos insuficientes, 401 para no autenticado (nunca intercambiarlos)

---

## Patrón 8 — Rate Limiting Seguro

**Dos niveles obligatorios:**

| Nivel | Aplica a | Clave | Límite sugerido |
|---|---|---|---|
| Por IP | Endpoints públicos (/login, /refresh) | `client_ip` | 10 req / 15 min |
| Por usuario | Endpoints autenticados | `user_id` | Por rol (VIEWER/EDITOR/ADMIN) |

**Rate limiting por IP (endpoints públicos):**
```python
_login_windows: dict[str, list[float]] = {}
LOGIN_LIMIT, LOGIN_WINDOW = 10, 900  # 10 intentos / 15 min

def check_login_rate_limit(client_ip: str) -> bool:
    now = time.time()
    window = [t for t in _login_windows.get(client_ip, []) if now - t < LOGIN_WINDOW]
    if len(window) >= LOGIN_LIMIT:
        return False
    window.append(now)
    _login_windows[client_ip] = window
    return True
```

**Purga periódica obligatoria** (aplicar en cada check o como tarea periódica):
```python
def purge_rate_windows(windows: dict, window_seconds: int) -> None:
    now = time.time()
    stale = [k for k, ts in windows.items() if not any(now - t < window_seconds for t in ts)]
    for k in stale:
        del windows[k]
```

**Checklist Rate Limiting:**
- [ ] /auth/login y /auth/refresh tienen rate limiting por IP
- [ ] Endpoints autenticados tienen rate limiting por usuario/rol
- [ ] HTTP 429 con mensaje genérico (no revelar límites exactos)
- [ ] Purga de ventanas expiradas implementada

---

## Patrón 9 — CORS Seguro

```python
from fastapi.middleware.cors import CORSMiddleware

# NUNCA allow_origins=["*"] cuando allow_credentials=True
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

---

## Patrón 10 — Security Headers

```python
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "0"  # CSP es preferible en browsers modernos
    return response
```

---

## Patrón 11 — Audit Logging Completo

**Registrar TODOS los eventos de seguridad, incluidos fallos:**

```python
# Intentos fallidos de login (sin contraseña en los logs)
store.audit_log.append({
    "user_id": None,
    "email_attempted": body.email,  # para detección de fuerza bruta, NO la contraseña
    "endpoint": "/auth/login",
    "method": "POST",
    "timestamp": datetime.utcnow().isoformat(),
    "status_code": 401,
    "event": "login_failed"
})
```

**Checklist Audit Logging:**
- [ ] Intentos fallidos de login registrados (sin contraseña)
- [ ] Accesos denegados (403) registrados
- [ ] status_code real capturado (no asumido como 200)
- [ ] Ningún dato sensible en los logs (passwords, tokens completos)

---

## Patrón 12 — In-Memory Store: Límites y Purga

**Todo dict in-memory que crezca indefinidamente DEBE tener purga:**

```python
def purge_expired_tokens(revoked_tokens: dict) -> None:
    """Llamar en cada check de revocación para evitar crecimiento ilimitado."""
    now = time.time()
    expired = [jti for jti, exp in revoked_tokens.items() if exp < now]
    for jti in expired:
        del revoked_tokens[jti]
```

**Limitaciones conocidas del POC in-memory (documentar siempre):**
- Tokens revocados se pierden al reiniciar → en producción usar Redis
- Race conditions sin locks → en producción usar base de datos con transacciones ACID
- Audit log mutable → en producción enviar a sistema de logs externo inmutable

---

## Patrón 13 — SCA: Análisis de Composición de Software

**Obligatorio en toda auditoría de seguridad.** El SecurityAgent DEBE revisar `requirements.txt`
(y `requirements-test.txt`) como parte del scope de auditoría, no solo los archivos `src/`.

**Herramienta:**
```bash
pip audit                        # Comprueba CVEs contra PyPA Advisory Database
pip audit --fix                  # Modo interactivo para actualizar paquetes vulnerables
```

**Criterios de evaluación por dependencia:**
1. ¿Tiene CVEs activos sin parchear?
2. ¿Tiene mantenimiento activo (commits recientes, respuesta a issues de seguridad)?
3. ¿Existe una alternativa más segura con API compatible?

**Dependencias de riesgo conocido en el stack Python/FastAPI:**

| Paquete | Riesgo | Alternativa |
|---|---|---|
| `python-jose` | CVE-2024-33664, CVE-2024-33663 | `PyJWT >= 2.8.0` |
| `python-multipart < 0.0.7` | DoS en parsing | Actualizar a `>= 0.0.7` |
| `starlette < 0.36.2` | Path traversal | Actualizar vía `fastapi` |

**Denylist permanente — rechazo automático sin excepción:**

| Paquete | Estado | Alternativa |
|---|---|---|
| `litellm` | PROHIBIDO — vulnerabilidad de seguridad | `anthropic` SDK directo |

```bash
# Verificación obligatoria Gate 2b — SecurityAgent
grep -rn "litellm" requirements*.txt pyproject.toml sdk/ 2>/dev/null \
  && echo "FAIL: dependencia prohibida detectada" && exit 1 \
  || echo "PASS: sin dependencias prohibidas"
```

**Checklist SCA:**
- [ ] `requirements.txt` incluido en el scope de auditoría
- [ ] `requirements-test.txt` incluido en el scope de auditoría
- [ ] `pip audit` ejecutado y sin hallazgos críticos o altos sin justificación
- [ ] Cada dependencia de terceros evaluada: CVEs + actividad de mantenimiento
- [ ] Ninguna dependencia con CVE activo sin mitigación documentada
- [ ] Ninguna dependencia de la denylist permanente presente en el proyecto

---

## Checklist de Seguridad Pre-Deploy

- [ ] **[SCA]** `pip audit` limpio sobre `requirements.txt` y `requirements-test.txt`
- [ ] **[SCA]** Ninguna dependencia con CVE activo sin mitigación documentada
- [ ] Ninguna credencial hardcodeada en el código fuente
- [ ] SECRET_KEY sin fallback — `os.environ["JWT_SECRET_KEY"]` lanza excepción si no está definida
- [ ] SECRET_KEY obtenida exclusivamente desde MCP / variable de entorno
- [ ] Logs no contienen passwords, tokens completos ni emails en texto plano
- [ ] Cost factor BCrypt benchmarkeado (≥ 100ms en hardware objetivo)
- [ ] Endpoint /login Y /refresh con rate limiting por IP activo
- [ ] JWT incluye campos `jti` e `iat`
- [ ] RBAC con ownership validation en operaciones de escritura
- [ ] Security headers configurados
- [ ] CORS con orígenes explícitos (nunca `*` con credenciales)
- [ ] Purga de tokens revocados expirados implementada
- [ ] **[bcrypt]** `max_length` en campo `password` es ≤ 72 (bcrypt>=4.1 lanza ValueError para >72 bytes → HTTP 500)
- [ ] Intentos fallidos de autenticación registrados en audit log
