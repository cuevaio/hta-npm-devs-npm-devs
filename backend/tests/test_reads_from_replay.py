"""get_vehicle_status y get_fleet_overview leen lo reproducido, con viajes y fletes sintéticos."""

from datetime import datetime, timedelta

import psycopg

from tests.helpers import KEY, REPLAY_START

CONTROL = "/v1/tools/control_replay"


def play_for(api, app, clock, **delta):
    api.post(CONTROL, headers=KEY, json={"action": "play"})
    clock.advance(**delta)
    app.state.replay_engine.tick()


def test_vehicle_status_shows_the_replayed_reading_and_its_synthetic_trip(api, app, clock):
    play_for(api, app, clock, minutes=10)  # T07 a las 20:30, con ~58 km/h

    body = api.get("/v1/tools/get_vehicle_status", params={"alias": "T07"}, headers=KEY).json()

    data = body["data"]
    assert data["alias"] == "T07"
    assert data["estado"] == "en_viaje"
    assert data["viaje_id"] == "T07-V01"
    assert data["corredor"] == "K01-K14" and data["sentido"] == "vuelta"
    assert data["conductor"] == "César Lazo"
    assert data["velocidad_kmh"] > 3
    assert datetime.fromisoformat(data["hora_evento"]) == REPLAY_START + timedelta(minutes=10)
    assert -90 <= data["posicion"]["lat"] <= 90
    assert {"fead_observed", "synthetic_demo"} <= set(body["provenance"])


def test_vehicle_status_is_idle_when_stopped_with_the_engine_on(api, app, clock):
    api.post(CONTROL, headers=KEY, json={"action": "seek", "to_event_time": "2020-04-03T19:50:00Z"})

    data = api.get("/v1/vehicles/T03").json()["data"]

    assert data["estado"] == "ralenti"
    assert data["velocidad_kmh"] == 0


def test_the_fleet_overview_changes_as_the_replay_advances(api, app, clock):
    before = api.get("/v1/fleet").json()["data"]
    api.post(CONTROL, headers=KEY, json={"action": "seek", "to_event_time": "2020-04-03T20:00:00Z"})
    after = api.get("/v1/fleet").json()

    assert [v["alias"] for v in before["vehiculos"]] == ["T07"]
    assert [v["alias"] for v in after["data"]["vehiculos"]] == ["T03", "T07"]
    assert after["data"]["total_vehiculos"] == 2
    assert after["data"]["viajes_en_curso"] == 2
    assert after["data"]["alertas_abiertas"] == 0
    assert after["time_range"]["to"].startswith("2020-04-03T20:00:00")


def test_a_vehicle_outside_any_trip_is_stopped_even_if_it_has_readings(api):
    api.post(CONTROL, headers=KEY, json={"action": "seek", "to_event_time": "2020-04-03T20:05:00Z"})
    with psycopg.connect(api.app.state.replay_engine.database_url) as conn:
        conn.execute("DELETE FROM driver_reports; DELETE FROM freights; DELETE FROM trips")

    data = api.get("/v1/vehicles/T07").json()["data"]

    assert data["viaje_id"] is None and data["conductor"] is None
    assert data["estado"] in ("detenido", "ralenti")


def test_unknown_alias_is_404_and_an_empty_database_gives_empty_lists(api, database_url):
    assert api.get("/v1/vehicles/T99").status_code == 404

    with psycopg.connect(database_url) as conn:
        conn.execute("TRUNCATE telemetry_reading, telemetry_source, driver_reports, freights, trips, drivers, vehicles")
    fleet = api.get("/v1/fleet").json()["data"]

    assert fleet["vehiculos"] == [] and fleet["total_vehiculos"] == 0
    assert api.get("/v1/vehicles/T07").status_code == 404


def test_every_trip_has_exactly_one_synthetic_freight(loaded):
    with psycopg.connect(loaded) as conn:
        rows = conn.execute(
            "SELECT t.trip_id, count(f.*), min(f.provenance), min(t.provenance) FROM trips t "
            "LEFT JOIN freights f USING (trip_id) GROUP BY t.trip_id"
        ).fetchall()
        drivers = conn.execute("SELECT DISTINCT provenance FROM drivers").fetchall()

    assert rows
    assert all(n == 1 and fp == "synthetic_demo" and tp == "synthetic_demo" for _, n, fp, tp in rows)
    assert drivers == [("synthetic_demo",)]
