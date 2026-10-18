import pytest
from fastapi.testclient import TestClient

from app.main import create_app

TOOL_GETS = [
    "/v1/tools/get_fleet_overview", "/v1/tools/get_vehicle_status?alias=T03",
    "/v1/tools/get_trip_status?trip_id=V-001", "/v1/tools/get_fuel_analysis?trip_id=V-001",
    "/v1/tools/get_operational_bottlenecks?trip_id=V-001", "/v1/tools/get_alerts",
]
PUBLIC = ["/v1/fleet", "/v1/vehicles/T03", "/v1/trips/V-001", "/v1/trips/V-001/fuel",
          "/v1/trips/V-001/bottlenecks", "/v1/alerts", "/v1/replay"]


@pytest.fixture
def api():
    return TestClient(create_app(api_key="secreta", cors_origins=["https://dashboard.example.com"]))


@pytest.mark.parametrize("path", TOOL_GETS)
def test_tools_without_key_are_401(api, path):
    assert api.get(path).status_code == 401


@pytest.mark.parametrize("path", TOOL_GETS)
def test_tools_with_wrong_key_are_401(api, path):
    assert api.get(path, headers={"X-API-Key": "otra"}).status_code == 401


@pytest.mark.parametrize("path", TOOL_GETS)
def test_tools_with_right_key_are_200(api, path):
    assert api.get(path, headers={"X-API-Key": "secreta"}).status_code == 200


def test_control_replay_requires_key(api):
    body = {"action": "play"}
    assert api.post("/v1/tools/control_replay", json=body).status_code == 401
    assert api.post("/v1/tools/control_replay", json=body, headers={"X-API-Key": "x"}).status_code == 401
    assert api.post("/v1/tools/control_replay", json=body, headers={"X-API-Key": "secreta"}).status_code == 200


@pytest.mark.parametrize("path", PUBLIC)
def test_dashboard_reads_are_public(api, path):
    assert api.get(path).status_code == 200


def test_protected_routes_are_503_when_api_key_is_not_configured(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    api = TestClient(create_app())

    assert api.get("/v1/tools/get_alerts", headers={"X-API-Key": "lo-que-sea"}).status_code == 503
    assert api.post("/v1/tools/control_replay", json={"action": "play"}).status_code == 503
    assert api.get("/v1/fleet").status_code == 200


def test_api_key_is_read_from_env(monkeypatch):
    monkeypatch.setenv("API_KEY", "del-entorno")
    api = TestClient(create_app())

    assert api.get("/v1/tools/get_alerts", headers={"X-API-Key": "del-entorno"}).status_code == 200


def _preflight(api, origin, method="GET"):
    return api.options(
        "/v1/fleet",
        headers={"Origin": origin, "Access-Control-Request-Method": method, "Access-Control-Request-Headers": "x-api-key"},
    )


@pytest.mark.parametrize("origin", ["https://x-preview.vercel.app", "https://dashboard.example.com"])
def test_cors_allows_vercel_previews_and_configured_origins(api, origin):
    response = _preflight(api, origin)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert "x-api-key" in response.headers["access-control-allow-headers"].lower()


@pytest.mark.parametrize("origin", ["https://evil.example.org", "https://vercel.app.evil.org"])
def test_cors_rejects_other_origins(api, origin):
    assert "access-control-allow-origin" not in _preflight(api, origin).headers


def test_cors_origins_come_from_env(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example.com, https://b.example.com")
    api = TestClient(create_app())

    assert _preflight(api, "https://b.example.com").headers["access-control-allow-origin"] == "https://b.example.com"
