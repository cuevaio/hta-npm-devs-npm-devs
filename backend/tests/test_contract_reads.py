from datetime import datetime

import pytest
from app.schemas import (
    AlertList, Bottlenecks, Envelope, FleetOverview, FuelAnalysis, Provenance, ReplayState,
    TripStatus, VehicleStatus,
)

from tests.helpers import KEY

# (ruta pública, ruta de la tool, modelo de data)
READS = [
    ("/v1/fleet", "/v1/tools/get_fleet_overview", FleetOverview),
    ("/v1/vehicles/T07", "/v1/tools/get_vehicle_status?alias=T07", VehicleStatus),
    ("/v1/trips/T07-V01", "/v1/tools/get_trip_status?trip_id=T07-V01", TripStatus),
    ("/v1/trips/T07-V01/fuel", "/v1/tools/get_fuel_analysis?trip_id=T07-V01", FuelAnalysis),
    ("/v1/trips/V-001/bottlenecks", "/v1/tools/get_operational_bottlenecks?trip_id=V-001", Bottlenecks),
    ("/v1/alerts", "/v1/tools/get_alerts", AlertList),
    ("/v1/replay", None, ReplayState),
]


def _cases():
    return list(_gen_cases())


def _gen_cases():
    for public, tool, model in READS:
        yield pytest.param(public, {}, model, id=public)
        if tool:
            yield pytest.param(tool, KEY, model, id=tool.split("?")[0])


@pytest.mark.parametrize("path,headers,model", _cases())
def test_read_returns_200_and_valid_envelope(api, path, headers, model):
    response = api.get(path, headers=headers)

    assert response.status_code == 200
    body = Envelope[model].model_validate(response.json())
    assert body.is_replay is True


@pytest.mark.parametrize("path,headers,model", _cases())
def test_every_response_declares_provenance_time_range_and_updated_at(api, path, headers, model):
    body = api.get(path, headers=headers).json()

    assert body["provenance"]
    assert all(p in {e.value for e in Provenance} for p in body["provenance"])
    assert datetime.fromisoformat(body["time_range"]["from"]) <= datetime.fromisoformat(body["time_range"]["to"])
    updated = datetime.fromisoformat(body["updated_at"])
    assert updated.utcoffset().total_seconds() == 0


@pytest.mark.parametrize(
    "path",
    ["/v1/vehicles/T99", "/v1/trips/V-999", "/v1/trips/V-999/fuel", "/v1/trips/V-999/bottlenecks",
     "/v1/tools/get_vehicle_status?alias=T99", "/v1/tools/get_trip_status?trip_id=V-999",
     "/v1/tools/get_fuel_analysis?trip_id=V-999", "/v1/tools/get_operational_bottlenecks?trip_id=V-999"],
)
def test_unknown_alias_or_trip_is_404_with_clear_body(api, path):
    response = api.get(path, headers=KEY)

    assert response.status_code == 404
    assert "desconocido" in response.json()["detail"]


def test_alert_includes_driver_report_with_human_reported_provenance(api):
    alerta = api.get("/v1/alerts").json()["data"]["alertas"][0]

    assert alerta["reporte_conductor"]["procedencia"] == "human_reported"


def test_control_replay_changes_the_state_seen_by_the_dashboard(api):
    assert api.get("/v1/replay").json()["data"]["estado"] == "paused"

    play = api.post("/v1/tools/control_replay", headers=KEY, json={"action": "play"})
    api.post("/v1/tools/control_replay", headers=KEY, json={"action": "set_speed", "speed": 60})
    api.post("/v1/tools/control_replay", headers=KEY, json={"action": "seek", "to_event_time": "2020-04-02T00:00:00Z"})

    assert play.status_code == 200
    data = api.get("/v1/replay").json()["data"]
    assert data["estado"] == "playing"
    assert data["velocidad"] == 60
    assert data["hora_replay"].startswith("2020-04-02T00:00:00")


@pytest.mark.parametrize(
    "body",
    [{"action": "set_speed"}, {"action": "seek"}, {"action": "seek", "to_event_time": "2030-01-01T00:00:00Z"},
     {"action": "rewind"}, {"action": "set_speed", "speed": 0}],
)
def test_control_replay_rejects_invalid_requests(api, body):
    assert api.post("/v1/tools/control_replay", headers=KEY, json=body).status_code == 422
