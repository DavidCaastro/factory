# SKILL: Layered Architecture — FastAPI Transport → Domain → Data
> Skill de carga perezosa. Cargar por Domain Orchestrators y CodeImplementers en tareas de backend.

## Contexto de Aplicación
- **Agentes:** BackendOrchestrator, CodeImplementer, DBArchitect, APIDesigner
- **Stack:** Python 3.10 + FastAPI
- **Regla de oro:** El flujo de dependencias es unidireccional: Transport → Domain → Data. Nunca al revés.

---

## Estructura de Carpetas

```
src/
├── main.py                    ← Entry point FastAPI, registra routers
├── transport/                 ← Capa Transporte
│   ├── __init__.py
│   ├── routers/
│   │   └── auth_router.py     ← Endpoints HTTP
│   └── schemas/
│       └── auth_schemas.py    ← Pydantic request/response models
├── domain/                    ← Capa Dominio
│   ├── __init__.py
│   ├── services/
│   │   └── auth_service.py    ← Lógica de negocio pura
│   ├── models/
│   │   └── user.py            ← Entidades de dominio (sin ORM)
│   └── cache/
│       └── token_cache.py     ← Caché en memoria (dict)
└── data/                      ← Capa Datos
    ├── __init__.py
    └── repositories/
        └── user_repository.py ← Acceso a BD exclusivamente vía MCP
```

---

## Patrón 1: Capa Transporte

**Responsabilidades:** Recibir HTTP, validar entrada, delegar al dominio, formatear respuesta.
**No contiene:** Lógica de negocio, acceso a datos, credenciales.

```python
# transport/schemas/auth_schemas.py
from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str  # nunca se loguea ni persiste

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

```python
# transport/routers/auth_router.py
from fastapi import APIRouter, HTTPException, Depends, status
from transport.schemas.auth_schemas import LoginRequest, TokenResponse
from domain.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

def get_auth_service() -> AuthService:
    return AuthService()

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, service: AuthService = Depends(get_auth_service)):
    token = await service.authenticate(body.email, body.password)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=token)
```

---

## Patrón 2: Capa Dominio

**Responsabilidades:** Lógica de negocio pura. Sin dependencias de FastAPI, sin SQL directo.
**No contiene:** Schemas HTTP, imports de FastAPI, credenciales, SQL.

```python
# domain/models/user.py
from dataclasses import dataclass

@dataclass
class User:
    id: str
    email: str
    hashed_password: str
```

```python
# domain/services/auth_service.py
import bcrypt
import jwt
import os
from datetime import datetime, timedelta, timezone
from domain.models.user import User
from data.repositories.user_repository import UserRepository

class AuthService:
    def __init__(self):
        self._repo = UserRepository()
        # SECRET_KEY SIEMPRE desde variable de entorno. Nunca hardcodeada.
        self._secret = os.environ["JWT_SECRET_KEY"]

    async def authenticate(self, email: str, password: str) -> str | None:
        user = await self._repo.find_by_email(email)

        # Anti-timing attack: siempre ejecutar checkpw aunque el usuario no exista
        dummy_hash = "$2b$12$dummy.hash.to.prevent.timing.attacks.padding"
        candidate_hash = user.hashed_password if user else dummy_hash

        if not bcrypt.checkpw(password.encode(), candidate_hash.encode()):
            return None
        if user is None:
            return None

        return self._create_token(user.id)

    def _create_token(self, subject: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": subject,
            "iat": now,
            "exp": now + timedelta(hours=1),
            "jti": os.urandom(16).hex(),  # para soporte de revocación
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")
```

---

## Patrón 3: Capa Datos

**Responsabilidades:** Acceso a BD exclusivamente vía MCP. Traducir entre entidades de dominio y persistencia.
**No contiene:** Lógica de negocio, validaciones, credenciales en código.

```python
# data/repositories/user_repository.py
from domain.models.user import User

class UserRepository:
    """
    Acceso a PostgreSQL exclusivamente vía MCP.
    Las credenciales de conexión las gestiona el servidor MCP local,
    nunca aparecen en este archivo.
    """

    async def find_by_email(self, email: str) -> User | None:
        # En producción: invocar herramienta MCP de BD
        # En POC/test: simulación de respuesta
        mock_db = {
            "test@example.com": User(
                id="usr_001",
                email="test@example.com",
                # hash bcrypt de "password123" con cost 12
                hashed_password="$2b$12$...",
            )
        }
        return mock_db.get(email)
```

---

## Patrón 4: Entry Point

```python
# main.py
from fastapi import FastAPI
from transport.routers.auth_router import router as auth_router

app = FastAPI(title="POC Login Seguro PIV/OAC")
app.include_router(auth_router)
```

---

## Patrón 5: Dependency Injection entre Capas

La capa Dominio no importa nada de Transport. La capa Datos no importa nada de Domain ni Transport.
Las dependencias se inyectan hacia abajo usando el sistema de `Depends` de FastAPI solo en la capa Transport:

```
Transport   →  usa Depends() para obtener instancias de servicios de Dominio
Domain      →  instancia directa de repositorios de Datos en su __init__
Data        →  no importa nada de las capas superiores
```

---

## Patrón 6: Reglas de Importación (Anti-Violación de Capas)

```python
# PERMITIDO:
from transport.schemas import ...    # dentro de transport/
from domain.services import ...      # desde transport/ hacia domain/
from domain.models import ...        # desde transport/ o data/ hacia domain/
from data.repositories import ...    # desde domain/ hacia data/

# PROHIBIDO:
# Desde domain/ importar algo de transport/
# Desde data/ importar algo de domain/ o transport/
# Credenciales literales en cualquier capa
```

---

## Checklist de Validación de Arquitectura

- [ ] `transport/` no contiene lógica de negocio
- [ ] `domain/` no importa nada de `transport/` ni de FastAPI
- [ ] `data/` no importa nada de `domain/` ni de `transport/`
- [ ] `SECRET_KEY` obtenida de `os.environ`, no hardcodeada
- [ ] `UserRepository` no tiene credenciales de BD en el código
- [ ] `checkpw` se ejecuta aunque el usuario no exista (anti-timing)
- [ ] Mensaje HTTP 401 es genérico, no distingue email vs contraseña
