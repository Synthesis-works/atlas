import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from unittest.mock import MagicMock

from apps.backend.main import app
from apps.backend.dependencies import get_auth_service
from atlas_db.models.core import User

client = TestClient(app)
mock_auth_service = MagicMock()

def override_get_auth_service():
    return mock_auth_service

app.dependency_overrides[get_auth_service] = override_get_auth_service

@pytest.fixture(autouse=True)
def reset_mocks():
    mock_auth_service.reset_mock()

def test_register_user_success():
    mock_auth_service.register_user.return_value = User(
        id=uuid4(),
        email="test@example.com",
        full_name="Test User",
        is_active=True,
        is_verified=False
    )
    
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "full_name": "Test User",
        "password": "password123"
    })
    
    assert response.status_code == 201
    data = response.json()
    assert data["data"]["email"] == "test@example.com"
    assert data["data"]["full_name"] == "Test User"
    assert "password_hash" not in data["data"]
    assert mock_auth_service.register_user.called

def test_login_user_success():
    from apps.backend.schemas.auth import TokenResponse
    
    mock_auth_service.authenticate_user.return_value = TokenResponse(
        access_token="mocked.jwt.token",
        token_type="bearer"
    )
    
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["data"]["access_token"] == "mocked.jwt.token"
    assert mock_auth_service.authenticate_user.called

def test_missing_jwt_token():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["message"] in ("Not authenticated", "Could not validate credentials", "Invalid token payload")

def test_malformed_jwt_token():
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer malformed.token.here"})
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Could not validate credentials"

import jwt
from datetime import datetime, timedelta, timezone
from apps.backend.config import settings

def test_expired_jwt_token():
    expire = datetime.now(timezone.utc) - timedelta(minutes=15) # expired 15 mins ago
    iat = datetime.now(timezone.utc) - timedelta(minutes=30)
    to_encode = {"sub": str(uuid4()), "exp": expire, "iat": iat, "jti": str(uuid4())}
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {encoded_jwt}"})
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Could not validate credentials"


