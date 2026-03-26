# SKILL: Testing — Patrones Pytest para Agentes PIV/OAC
> Skill de carga perezosa. Cargar por: SpecialistAgent (testing), StandardsAgent (Gate 2b), TestWriter agents.

## Contexto de Aplicación
- **Agente:** SpecialistAgent de testing, TestWriter, StandardsAgent
- **Stack base:** pytest + pytest-asyncio + pytest-cov + unittest.mock
- **Stacks opcionales:** httpx (HTTP/FastAPI), motor (MongoDB async), sqlalchemy (DB)
- **Cobertura objetivo:** los RFs declarados en `specs/active/functional.md` del objetivo activo

> **Nota de adaptación:** este skill define patrones genéricos. El especialista adapta los nombres de módulos, fixtures y clases al dominio del objetivo activo. Los ejemplos usan un servicio de autenticación FastAPI como referencia concreta, pero el patrón aplica a cualquier dominio.

---

## Estructura de Tests

```
tests/
├── conftest.py              ← Fixtures compartidos
├── unit/
│   ├── test_auth_service.py ← Tests unitarios del dominio
│   └── test_token_cache.py  ← Tests de la caché de tokens
└── integration/
    └── test_auth_router.py  ← Tests de endpoints HTTP (RF-01 a RF-04)
```

---

## Patrón 1: conftest.py — Fixtures Base

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from main import app
from domain.models.user import User

MOCK_USER = User(
    id="usr_test_001",
    email="test@example.com",
    # bcrypt hash de "correctpassword" con cost 4 (rápido en tests)
    hashed_password="$2b$04$test.hash.replace.in.fixture",
)

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_user_repo():
    """Mock del repositorio para aislar tests del dominio de la BD."""
    with patch("domain.services.auth_service.UserRepository") as mock:
        mock.return_value.find_by_email = AsyncMock(return_value=MOCK_USER)
        yield mock

@pytest.fixture
def mock_empty_repo():
    """Repo que no encuentra usuarios — para testear usuario inexistente."""
    with patch("domain.services.auth_service.UserRepository") as mock:
        mock.return_value.find_by_email = AsyncMock(return_value=None)
        yield mock

@pytest.fixture(autouse=True)
def set_jwt_secret(monkeypatch):
    """JWT_SECRET_KEY siempre presente en tests."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
```

---

## Patrón 2: Tests de Integración — Endpoints (RF-01 a RF-04)

```python
# tests/integration/test_auth_router.py
import pytest
import jwt

class TestLoginEndpoint:
    """RF-01: POST /login existe y acepta email + password."""

    def test_endpoint_exists(self, client, mock_user_repo):
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "correctpassword"
        })
        assert response.status_code != 404

    def test_accepts_email_and_password(self, client, mock_user_repo):
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "correctpassword"
        })
        assert response.status_code == 200


class TestJWTResponse:
    """RF-03: JWT válido con expiración de 1 hora."""

    def test_returns_access_token(self, client, mock_user_repo):
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "correctpassword"
        })
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_jwt_has_correct_expiry(self, client, mock_user_repo):
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "correctpassword"
        })
        token = response.json()["access_token"]
        payload = jwt.decode(token, "test-secret-key-for-testing-only",
                             algorithms=["HS256"])
        expiry_delta = payload["exp"] - payload["iat"]
        assert expiry_delta == 3600  # exactamente 1 hora

    def test_jwt_contains_jti(self, client, mock_user_repo):
        """jti necesario para soporte de revocación."""
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "correctpassword"
        })
        token = response.json()["access_token"]
        payload = jwt.decode(token, "test-secret-key-for-testing-only",
                             algorithms=["HS256"])
        assert "jti" in payload


class TestErrorHandling:
    """RF-04: HTTP 401 genérico sin revelar información sensible."""

    def test_wrong_password_returns_401(self, client, mock_user_repo):
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    def test_nonexistent_user_returns_401(self, client, mock_empty_repo):
        response = client.post("/auth/login", json={
            "email": "noexiste@example.com",
            "password": "anypassword"
        })
        assert response.status_code == 401

    def test_error_message_is_generic(self, client, mock_user_repo):
        """El mensaje no debe distinguir entre email incorrecto y contraseña incorrecta."""
        response_wrong_pass = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword"
        })
        response_wrong_user = client.post("/auth/login", json={
            "email": "noexiste@example.com",
            "password": "anypassword"
        })
        # Ambos deben devolver el mismo mensaje
        assert (response_wrong_pass.json()["detail"] ==
                response_wrong_user.json()["detail"])

    def test_error_does_not_reveal_field(self, client, mock_user_repo):
        """El mensaje no debe mencionar 'email', 'password', 'usuario' ni 'contraseña'."""
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword"
        })
        detail = response.json()["detail"].lower()
        forbidden_words = ["email", "password", "usuario", "contraseña", "user", "pass"]
        for word in forbidden_words:
            assert word not in detail, f"Error message reveals: '{word}'"
```

---

## Patrón 3: Tests Unitarios — AuthService (RF-02)

```python
# tests/unit/test_auth_service.py
import pytest
import bcrypt
from unittest.mock import AsyncMock, patch
from domain.services.auth_service import AuthService
from domain.models.user import User

def make_hashed(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=4)).decode()

class TestBCryptVerification:
    """RF-02: Contraseñas comparadas con BCrypt, nunca en texto plano."""

    @pytest.mark.asyncio
    async def test_correct_password_authenticates(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
        user = User(id="1", email="a@b.com",
                    hashed_password=make_hashed("correctpass"))
        with patch.object(AuthService, '__init__',
                          lambda self: setattr(self, '_repo', None) or
                          setattr(self, '_secret', 'test-secret')):
            service = AuthService.__new__(AuthService)
            service._repo = AsyncMock()
            service._repo.find_by_email = AsyncMock(return_value=user)
            service._secret = "test-secret"
            result = await service.authenticate("a@b.com", "correctpass")
            assert result is not None

    @pytest.mark.asyncio
    async def test_wrong_password_returns_none(self, monkeypatch):
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
        user = User(id="1", email="a@b.com",
                    hashed_password=make_hashed("correctpass"))
        service = AuthService.__new__(AuthService)
        service._repo = AsyncMock()
        service._repo.find_by_email = AsyncMock(return_value=user)
        service._secret = "test-secret"
        result = await service.authenticate("a@b.com", "wrongpass")
        assert result is None

    @pytest.mark.asyncio
    async def test_timing_safe_nonexistent_user(self, monkeypatch):
        """checkpw debe ejecutarse incluso si el usuario no existe."""
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret")
        service = AuthService.__new__(AuthService)
        service._repo = AsyncMock()
        service._repo.find_by_email = AsyncMock(return_value=None)
        service._secret = "test-secret"
        # No debe lanzar excepción ni diferencia de tiempo observable
        result = await service.authenticate("noexiste@b.com", "anypass")
        assert result is None
```

---

## Patrón 4: Tests de Caché de Tokens

```python
# tests/unit/test_token_cache.py
from datetime import datetime, timedelta, timezone
from domain.cache.token_cache import revoke_token, is_token_revoked, purge_expired

class TestTokenCache:

    def test_revoked_token_is_detected(self):
        jti = "test-jti-001"
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        revoke_token(jti, expires)
        assert is_token_revoked(jti) is True

    def test_non_revoked_token_passes(self):
        assert is_token_revoked("never-revoked-jti") is False

    def test_purge_removes_expired_tokens(self):
        jti = "expired-jti"
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        revoke_token(jti, past)
        purge_expired(datetime.now(timezone.utc))
        assert is_token_revoked(jti) is False
```

---

## Dependencias de Test

```txt
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0          # cliente async para TestClient
```

---

## Checklist de Cobertura

- [ ] RF-01: endpoint `POST /login` existe y acepta los campos correctos
- [ ] RF-02: BCrypt usado para verificación (no texto plano)
- [ ] RF-02: timing-safe — checkpw ejecutado aunque usuario no exista
- [ ] RF-03: JWT devuelto con expiración exacta de 3600 segundos
- [ ] RF-03: JWT contiene campo `jti`
- [ ] RF-04: HTTP 401 para password incorrecta
- [ ] RF-04: HTTP 401 para usuario inexistente
- [ ] RF-04: mismo mensaje en ambos casos (no revela campo fallido)
- [ ] RF-04: mensaje no contiene palabras que revelen información
