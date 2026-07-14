from fastapi.testclient import TestClient
from services.dataset.main import app
import pytest

client = TestClient(app)

def test_api_availability():
    # Just a simple sanity check that the app mounts
    assert app.title == "Atlas Dataset Service"
