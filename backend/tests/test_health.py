from fastapi.testclient import TestClient

from app.main import create_app


def test_health_reports_postgis(client):
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["postgis"]


def test_health_is_503_when_database_is_down():
    client = TestClient(create_app("postgresql://nobody:nothing@127.0.0.1:1/none"))

    response = client.get("/health")

    assert response.status_code == 503
