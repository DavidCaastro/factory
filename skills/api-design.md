# SKILL: API Design — Contratos, Schemas Pydantic y OpenAPI
> Skill de carga perezosa. Cargar SOLO por APIDesigner agents y Domain Orchestrators al definir contratos de interfaz.

## Contexto de Aplicación
- **Agente:** APIDesigner, BackendOrchestrator
- **Cuándo:** Antes de implementar cualquier endpoint — el contrato define qué implementan los CodeImplementers
- **Output esperado:** Schemas Pydantic completos + definición de endpoints + ejemplos de request/response

---

## Patrón 1: Principios de Diseño de Contratos

```
1. CONTRACT-FIRST: El schema define la implementación, no al revés.
   El APIDesigner entrega los schemas al CodeImplementer como input.

2. MÍNIMA EXPOSICIÓN: Solo exponer los campos que el cliente necesita.
   Nunca exponer campos internos (id interno, hash de password, timestamps internos).

3. TIPOS ESTRICTOS: Usar tipos específicos de Pydantic (EmailStr, HttpUrl, etc.)
   en lugar de str genérico donde sea posible.

4. VERSIONING: Prefijo /v1/ en todos los endpoints desde el inicio.
   Facilita evolución sin breaking changes.

5. CONSISTENCIA DE ERRORES: Todos los errores siguen el mismo schema.
```

---

## Patrón 2: Schemas de Request

```python
# transport/schemas/auth_schemas.py
from pydantic import BaseModel, EmailStr, Field

class LoginRequest(BaseModel):
    """
    Contrato de entrada para POST /v1/auth/login
    - email: validado como dirección de correo válida por Pydantic
    - password: string sin restricción de longitud máxima en request
                (BCrypt trunca a 72 bytes internamente)
    """
    email: EmailStr = Field(
        ...,
        description="Dirección de correo electrónico del usuario",
        example="usuario@empresa.com"
    )
    password: str = Field(
        ...,
        min_length=8,
        description="Contraseña del usuario (mínimo 8 caracteres)",
    )

    class Config:
        # Previene campos extra no declarados
        extra = "forbid"
```

---

## Patrón 3: Schemas de Response

```python
class TokenResponse(BaseModel):
    """
    Contrato de respuesta exitosa para POST /v1/auth/login
    Sigue el estándar OAuth2 Bearer Token.
    """
    access_token: str = Field(
        ...,
        description="JWT firmado con HS256"
    )
    token_type: str = Field(
        default="bearer",
        description="Tipo de token. Siempre 'bearer'."
    )
    expires_in: int = Field(
        default=3600,
        description="Segundos hasta la expiración del token"
    )

class ErrorResponse(BaseModel):
    """
    Schema unificado para todos los errores.
    FastAPI usa HTTPException pero documentamos el formato.
    """
    detail: str = Field(
        ...,
        description="Mensaje de error genérico. No revela información sensible.",
        example="Credenciales inválidas."
    )
```

---

## Patrón 4: Definición de Endpoints

```
POST /v1/auth/login
───────────────────
Propósito:    Autenticar usuario y obtener JWT
Request:      LoginRequest (application/json)
Response 200: TokenResponse
Response 401: ErrorResponse {"detail": "Credenciales inválidas."}
Response 422: ValidationError (Pydantic — campo faltante o formato incorrecto)

Headers de respuesta 401:
  WWW-Authenticate: Bearer

Idempotente: NO (genera un nuevo token en cada llamada exitosa)
Auth requerida: NO (es el endpoint de autenticación)
Rate limit recomendado: 10 intentos / minuto por IP
```

---

## Patrón 5: Documentación OpenAPI (automática con FastAPI)

```python
# Enriquecer la documentación automática de FastAPI:

@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        200: {
            "description": "Autenticación exitosa",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "expires_in": 3600
                    }
                }
            }
        },
        401: {
            "description": "Credenciales inválidas",
            "content": {
                "application/json": {
                    "example": {"detail": "Credenciales inválidas."}
                }
            }
        }
    },
    summary="Autenticación de usuario",
    description="Valida email y contraseña. Devuelve JWT con expiración de 1 hora."
)
async def login(body: LoginRequest, ...):
    ...
```

---

## Patrón 6: Evolución del Contrato (Reglas)

```
BREAKING CHANGES (requieren nueva versión /v2/):
  - Eliminar o renombrar campos del request
  - Cambiar tipo de un campo existente
  - Hacer obligatorio un campo opcional

NON-BREAKING (se pueden hacer en /v1/):
  - Añadir campos opcionales al response
  - Añadir nuevos endpoints
  - Añadir validaciones más permisivas

NUNCA:
  - Cambiar el significado de un campo sin cambiar su nombre
  - Eliminar un campo del response sin deprecación previa
```

---

## Checklist de Contrato

- [ ] Request schema usa `EmailStr` para el campo email
- [ ] Request schema tiene `extra = "forbid"` (no campos extra)
- [ ] Response de éxito sigue estándar OAuth2 Bearer
- [ ] Response de error es genérico y consistente
- [ ] Todos los campos tienen `description` y `example`
- [ ] Endpoint documentado con `responses` para 200 y 401
- [ ] Prefijo `/v1/` en la ruta
- [ ] `WWW-Authenticate: Bearer` en header del 401
