from fastapi.testclient import TestClient

from services.report.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "timestamp" in response.json()


def test_versions():
    response = client.get("/api/v1/versions")
    assert response.status_code == 200
    assert response.json()["service"] == "reporting-service"
