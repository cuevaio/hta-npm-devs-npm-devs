"""get_fuel_analysis: pasadas del viaje frente a la línea base de su tramo y sentido (ADR 0002, 0008, 0009, D33)."""

import os
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest
from scripts.load_demo_data import load

from tests.helpers import KEY, REPLAY_START

TRIP = "T07-V01"
FUEL = f"/v1/trips/{TRIP}/fuel"


def pasadas(api, path=FUEL):
    return api.get(path).json()["data"]["pasadas"]


def by_cell(data, n):
    return next(p for p in data if p["tramo"]["h3"] == f"861496000{n}fffff")


def test_overconsumption_needs_both_125_times_the_median_and_more_than_p90(api):
    data = pasadas(api)

    over = by_cell(data, 0)  # 52 >= 1,25 x 40 y > p90 45
    assert over["sobreconsumo"] is True
    assert over["exceso_l"] == pytest.approx(0.6)  # 2,6 L - mediana de 2,0 L
    assert over["linea_base"] == {"mediana_l": 2.0, "p90_l": 2.3, "n_pasadas": 5}
    assert over["consumo_observado_l"] == 2.6 and over["tramo"] == {"h3": "8614960000fffff", "sentido": "vuelta"}

    within_p90 = by_cell(data, 1)  # 52 >= 50 pero <= p90 de 60
    assert within_p90["sobreconsumo"] is False
    assert within_p90["exceso_l"] == pytest.approx(0.6)  # el exceso se informa igual

    normal = by_cell(data, 3)  # tramo con un solo vehículo: ver abajo
    assert normal["linea_base"] is None


def test_a_segment_without_enough_passes_or_peers_has_no_baseline_and_no_overconsumption(api):
    data = pasadas(api)

    few_passes = by_cell(data, 2)  # n_passes = 2
    one_vehicle = by_cell(data, 3)  # n_vehicles = 1: no hay pares
    for p in (few_passes, one_vehicle):
        assert p["linea_base"] is None
        assert p["sobreconsumo"] is False
        assert p["exceso_l"] is None


def test_trip_totals_are_sums_over_the_visible_passes_and_there_are_no_anomalies_yet(api):
    data = api.get(FUEL).json()["data"]

    assert data["viaje_id"] == TRIP
    assert len(data["pasadas"]) == 4
    assert data["consumo_observado_l"] == pytest.approx(2.6 + 2.6 + 2.0 + 1.6)
    assert data["distancia_km"] == pytest.approx(5.0 + 5.0 + 3.6 + 4.0)
    assert data["consumo_l_100km"] == pytest.approx(8.8 / 17.6 * 100, abs=0.1)
    assert data["exceso_total_l"] == pytest.approx(1.2)  # solo las pasadas con línea base: 0,6 + 0,6
    assert data["anomalias"] == []


def test_a_pass_after_the_replay_time_is_invisible_until_the_replay_reaches_it(api, app, clock):
    assert len(pasadas(api)) == 4

    api.post("/v1/tools/control_replay", headers=KEY, json={"action": "play"})
    clock.advance(minutes=10)  # 20:30, pasada futura termina 20:27
    app.state.replay_engine.tick()

    data = pasadas(api)
    assert len(data) == 5
    assert data[-1]["tramo"]["h3"] == "8614960004fffff" and data[-1]["sobreconsumo"] is True


def test_idle_minutes_come_from_stopped_readings_with_the_engine_on(api):
    data = pasadas(api)

    first = by_cell(data, 0)  # 20:08:00-20:11:00: telemetría desde 20:08:40, 38 s en ralentí en 20:08-20:12
    assert 0 < first["ralenti_min"] <= 3
    assert all(p["ralenti_min"] >= 0 for p in data)


def test_provenance_lists_observed_inferred_and_synthetic(api):
    body = api.get(FUEL).json()

    assert {"fead_observed", "model_inferred", "synthetic_demo"} <= set(body["provenance"])


def test_trip_status_reads_the_loaded_trip_with_freight_and_driver(api):
    data = api.get(f"/v1/trips/{TRIP}").json()["data"]

    assert data["viaje_id"] == TRIP and data["vehiculo_alias"] == "T07"
    assert data["conductor"] == "César Lazo" and data["flete"]["id"] == "F-102"
    assert data["corredor"] == "K01-K14" and data["sentido"] == "vuelta"
    assert data["estado"] == "en_curso" and 0 <= data["progreso_pct"] <= 100


def test_a_finished_trip_is_finalizado_with_its_end(api, loaded):
    with psycopg.connect(loaded) as conn:  # el rango del fixture no llega al fin del viaje: se adelanta el reloj
        conn.execute("UPDATE replay_state SET hora_replay = '2020-04-12T00:00:00Z'")

    data = api.get("/v1/trips/T07-V01").json()["data"]

    assert data["estado"] == "finalizado" and data["fin"] is not None


def test_unknown_trip_is_404(api):
    assert api.get("/v1/trips/NOPE/fuel").status_code == 404
    assert api.get("/v1/trips/NOPE").status_code == 404


def test_loader_is_idempotent_for_passes_and_baselines(loaded, source_dir):
    def counts():
        with psycopg.connect(loaded) as conn:
            return [conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("passes", "baselines")]

    assert counts() == [5, 5]
    load(source_dir, loaded, REPLAY_START)
    assert counts() == [5, 5]


# --- Datos reales (salida del pipeline de data/), se salta sin FLEET_DATA_DIR ---

REAL = os.environ.get("FLEET_DATA_DIR")


@pytest.fixture(scope="module")
def real_api(database_url):
    from app.main import create_app
    from fastapi.testclient import TestClient

    load(Path(REAL), database_url, datetime(2020, 4, 12, 16, 0, tzinfo=UTC))
    with psycopg.connect(database_url) as conn:  # el replay al final: todas las pasadas visibles
        conn.execute("UPDATE replay_state SET hora_replay = fin")
    yield TestClient(create_app(database_url))


def _window(api, trip, start_utc8, end_utc8):
    """Pasadas del viaje cuyo tramo cae en la ventana (hora local UTC+8) dada."""
    tz = datetime.fromisoformat
    lo, hi = tz(start_utc8 + "+08:00"), tz(end_utc8 + "+08:00")
    with psycopg.connect(api.app.state.database_url) as conn:
        cells = [r[0] for r in conn.execute(
            "SELECT h3_cell FROM passes WHERE trip_id = %s AND t_start >= %s AND t_end <= %s", (trip, lo, hi))]
    data = api.get(f"/v1/trips/{trip}/fuel").json()["data"]["pasadas"]
    return [p for p in data if p["tramo"]["h3"] in cells]


@pytest.mark.skipif(not REAL, reason="FLEET_DATA_DIR no está definido")
def test_real_t07_climbing_nanling_stays_within_the_norm(real_api):
    trips = real_api.app.state.database_url
    with psycopg.connect(trips) as conn:
        trip = conn.execute(
            "SELECT trip_id FROM trips WHERE alias = 'T07' AND t_start <= %s AND t_end >= %s",
            (datetime.fromisoformat("2020-04-08T06:49+08:00"), datetime.fromisoformat("2020-04-08T07:06+08:00")),
        ).fetchone()[0]
    segment = _window(real_api, trip, "2020-04-08T06:49", "2020-04-08T07:06")

    assert segment and all(p["sobreconsumo"] is False for p in segment), segment


@pytest.mark.skipif(not REAL, reason="FLEET_DATA_DIR no está definido")
@pytest.mark.xfail(strict=True, reason=(
    "BLOQUEADO (#14): en la salida real T28-V03 va por el corredor K11-K17 (ida), que solo tiene 1 fila de línea "
    "base y ninguna en esas celdas; ninguna pasada de T28 el 2020-04-07 (UTC+8 ni UTC) vale ~90,5 L/100 km. "
    "Hay que decidir el escenario de la Demo A sobre otra pasada o recalcular los corredores en data/."))
def test_real_t28_demo_a_segment_shows_overconsumption(real_api):
    with psycopg.connect(real_api.app.state.database_url) as conn:
        trip = conn.execute(
            "SELECT trip_id FROM trips WHERE alias = 'T28' AND t_start <= %s AND t_end >= %s",
            (datetime.fromisoformat("2020-04-07T08:30+08:00"), datetime.fromisoformat("2020-04-07T08:48+08:00")),
        ).fetchone()[0]
    segment = _window(real_api, trip, "2020-04-07T08:30", "2020-04-07T08:48")

    assert any(p["sobreconsumo"] and p["exceso_l"] > 0 for p in segment), segment
