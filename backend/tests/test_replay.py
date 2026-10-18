"""Replay (ADR 0005): control vía control_replay, tick con reloj falso y lecturas con tres horas."""

from datetime import UTC, datetime, timedelta

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.main import create_app

from tests.helpers import KEY, REPLAY_START, T0

CONTROL = "/v1/tools/control_replay"


def control(api, **body):
    response = api.post(CONTROL, headers=KEY, json=body)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def replay(api):
    return api.get("/v1/replay").json()["data"]


def readings(url, where="replayed_at IS NOT NULL"):
    with psycopg.connect(url) as conn:
        return conn.execute(
            f"SELECT alias, event_time, replayed_at, ingested_at, ST_X(geom::geometry), ST_Y(geom::geometry), lat, lon "
            f"FROM telemetry_reading WHERE {where} ORDER BY alias, event_time"
        ).fetchall()


def test_replay_starts_paused_at_the_beginning_and_does_not_advance_while_paused(api, app, clock):
    assert replay(api)["estado"] == "paused"

    clock.advance(minutes=30)
    app.state.replay_engine.tick()

    data = replay(api)
    assert datetime.fromisoformat(data["hora_replay"]) == REPLAY_START
    assert readings(app.state.replay_engine.database_url) == []


def test_playing_advances_the_replay_clock_by_real_time_times_speed(api, app, clock):
    control(api, action="play")
    control(api, action="set_speed", speed=60)

    clock.advance(minutes=1)
    app.state.replay_engine.tick()

    assert datetime.fromisoformat(replay(api)["hora_replay"]) == REPLAY_START + timedelta(hours=1)


def test_pause_freezes_the_replay_and_play_resumes_from_there(api, app, clock):
    control(api, action="play")
    clock.advance(minutes=5)
    app.state.replay_engine.tick()
    paused = control(api, action="pause")
    assert paused["estado"] == "paused"

    clock.advance(minutes=30)
    app.state.replay_engine.tick()
    assert datetime.fromisoformat(replay(api)["hora_replay"]) == REPLAY_START + timedelta(minutes=5)

    control(api, action="play")
    clock.advance(minutes=1)
    app.state.replay_engine.tick()
    assert datetime.fromisoformat(replay(api)["hora_replay"]) == REPLAY_START + timedelta(minutes=6)


def test_a_speed_change_applies_only_from_that_moment(api, app, clock):
    control(api, action="play")
    clock.advance(minutes=1)  # 1 min a 1x
    control(api, action="set_speed", speed=10)
    clock.advance(minutes=1)  # 10 min a 10x
    app.state.replay_engine.tick()

    assert datetime.fromisoformat(replay(api)["hora_replay"]) == REPLAY_START + timedelta(minutes=11)


def test_replayed_readings_keep_event_time_replay_time_and_ingest_time_apart_with_a_postgis_position(api, app, clock):
    control(api, action="play")
    clock.advance(minutes=10)
    app.state.replay_engine.tick()

    rows = readings(app.state.replay_engine.database_url)
    assert rows
    for alias, event_time, replayed_at, ingested_at, x, y, lat, lon in rows:
        assert alias == "T07"
        assert REPLAY_START < event_time <= REPLAY_START + timedelta(minutes=10)
        assert replayed_at == REPLAY_START + timedelta(minutes=10)
        assert ingested_at == T0 + timedelta(minutes=10)
        assert (x, y) == pytest.approx((lon, lat))
    assert len({r[1] for r in rows}) == len(rows)  # sin duplicados


def test_seek_backwards_discards_what_was_replayed_after_that_point(api, app, clock):
    control(api, action="play")
    clock.advance(minutes=10)
    app.state.replay_engine.tick()
    before = len(readings(app.state.replay_engine.database_url))

    data = control(api, action="seek", to_event_time="2020-04-01T20:25:00Z")

    assert data["hora_replay"].startswith("2020-04-01T20:25:00")
    after = readings(app.state.replay_engine.database_url)
    assert 0 < len(after) < before
    assert all(r[1] <= datetime(2020, 4, 1, 20, 25, tzinfo=UTC) for r in after)


def test_seek_forwards_replays_everything_in_between(api, app):
    control(api, action="seek", to_event_time="2020-04-03T20:00:00Z")

    aliases = {r[0] for r in readings(app.state.replay_engine.database_url)}
    assert aliases == {"T07", "T03"}


def test_replay_stops_at_the_end_of_the_source(api, app, clock):
    control(api, action="play")
    control(api, action="set_speed", speed=1_000_000)
    clock.advance(hours=1)
    app.state.replay_engine.tick()

    data = replay(api)
    assert data["hora_replay"] == data["fin"]
    assert data["estado"] == "paused"


def _run(loaded, make_clock):
    clock = make_clock()
    api = TestClient(create_app(loaded, api_key="secreta", clock=clock))
    app = api.app
    control(api, action="play")
    control(api, action="set_speed", speed=120)
    for _ in range(5):
        clock.advance(seconds=30)
        app.state.replay_engine.tick()
    control(api, action="pause")
    control(api, action="seek", to_event_time="2020-04-03T20:05:00Z")
    return (
        api.get("/v1/replay").json(), api.get("/v1/fleet").json(), api.get("/v1/vehicles/T03").json(),
        readings(loaded),
    )


def test_same_replay_with_same_clock_gives_the_same_results(loaded, source_dir):
    from scripts.load_demo_data import load

    from tests.helpers import REPLAY_START as start, FakeClock

    first = _run(loaded, FakeClock)
    load(source_dir, loaded, start)
    second = _run(loaded, FakeClock)

    assert first == second
    assert first[3]  # y no es vacío


def test_the_replay_runs_as_an_asyncio_task_inside_the_api(loaded, clock):
    app = create_app(loaded, api_key="secreta", clock=clock, tick_interval=0.02)
    with TestClient(app) as api:
        control(api, action="play")
        clock.advance(minutes=10)
        import time

        deadline = time.time() + 5
        while time.time() < deadline and not readings(loaded):
            time.sleep(0.05)

        assert readings(loaded)
