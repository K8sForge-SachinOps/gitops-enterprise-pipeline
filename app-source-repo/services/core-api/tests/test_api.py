import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "version" in data
    assert "environment" in data

def test_healthz():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_readyz():
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"

def test_info_endpoint():
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    data = response.json()
    assert "Air-Gapped Ready" in data["compliance"]

def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "process_uptime_seconds" in response.text

def test_aiops_status():
    response = client.get("/api/v1/aiops/status")
    assert response.status_code == 200
    assert response.json()["cluster_health_score"] == 100.0
    assert "argocd" in response.json()["monitored_namespaces"]

def test_aiops_heal():
    response = client.post("/api/v1/aiops/heal")
    assert response.status_code == 200
    assert response.json()["result"] == "success"

