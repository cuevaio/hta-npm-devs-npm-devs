import csv
from datetime import UTC, datetime

import polars as pl
import psycopg

from scripts.load_demo_data import load
from tests.conftest import FIXTURES, REPO
from tests.helpers import KEY, REPLAY_START

CONTROL = "/v1/tools/control_replay"


def test_a_reading_without_position_is_loaded_replayed_and_keeps_the_last_known_position(
    database_url, source_dir, clock
):
    from fastapi.testclient import TestClient

    from app.main import create_app

    base = (FIXTURES / "telemetry.csv").read_text(encoding="utf-8")
    extra = (FIXTURES / "telemetry_sin_posicion.csv").read_text(encoding="utf-8").split("\n", 1)[1]
    (source_dir / "telemetry.csv").unlink()
    (source_dir / "telemetry.csv").write_text(base + extra, encoding="utf-8")
    load(source_dir, database_url, REPLAY_START)
    api = TestClient(create_app(database_url, api_key="secreta", clock=clock))
    known = next(r for r in csv.DictReader(open(FIXTURES / "telemetry.csv"))
                 if r["alias"] == "T07" and r["event_time"] == "2020-04-01T20:31:00Z")

    api.post(CONTROL, headers=KEY, json={"action": "seek", "to_event_time": "2020-04-01T20:31:00.7Z"})

    data = api.get("/v1/vehicles/T07").json()["data"]
    assert data["hora_evento"].startswith("2020-04-01T20:31:00.5")
    assert data["velocidad_kmh"] == 0 and data["estado"] == "ralenti"
    assert data["posicion"] == {"lat": float(known["lat"]), "lon": float(known["lon"])}
    with psycopg.connect(database_url) as conn:
        row = conn.execute(
            "SELECT lat, lon, geom, fuel_rate_lph FROM telemetry_reading WHERE replayed_at IS NOT NULL "
            "AND event_time = '2020-04-01T20:31:00.5Z'"
        ).fetchone()
    assert row == (None, None, None, 3.1)


def test_loader_reads_the_pipeline_parquet_layout(database_url, source_dir):
    (source_dir / "telemetry.csv").unlink()
    (source_dir / "telemetry").mkdir()
    df = pl.DataFrame({
        "alias": ["T03", "T03"],
        "event_time": [datetime(2020, 4, 12, 15, 59, 59, tzinfo=UTC), datetime(2020, 4, 12, 16, 0, 5, tzinfo=UTC)],
        "lat": [45.7, None], "lon": [126.7, None], "speed_kmh": [10.0, 0.0], "rpm": [900.0, 700.0],
        "fuel_rate_lph": [20.0, 3.0], "fuel_total_l": [1.0, 1.1], "odometer_km": [5.0, 5.0],
        "engine_on": [True, True], "provenance": ["fead_observed"] * 2,
    })
    df.write_parquet(source_dir / "telemetry" / "T03.parquet")

    counts = load(source_dir, database_url)  # corte por defecto: 2020-04-13 00:00 UTC+8

    assert counts == {"history": 1, "source": 1}
