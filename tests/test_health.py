import pytest
from fastapi.testclient import TestClient
from apps.backend.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert data["data"]["status"] == "ok"
    assert "version" in data["data"]
    assert "meta" in data
    assert "request_id" in data["meta"]
