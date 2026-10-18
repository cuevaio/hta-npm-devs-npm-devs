"""Tablero de fletes con el fixture de la flota de Perú (ADR 0012): capa comercial y consumo observado."""

from datetime import UTC, datetime

import polars as pl
import psycopg
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from scripts.load_demo_data import load
from tests.conftest import FIXTURES, REPO

PERU = REPO / "data" / "fixtures"


@pytest.fixture
def peru_source(tmp_path):
    for name in ("telemetry.csv", "drivers.csv", "driver_reports.csv", "trips.csv", "freights.csv"):
        (tmp_path / name).symlink_to(PERU / name)
    (tmp_path / "baseline.csv").symlink_to(PERU / "baseline_sample.csv")
    header = (FIXTURES / "passes_demo.csv").read_text(encoding="utf-8").split("\n", 1)[0]
    (tmp_path / "passes_demo.csv").write_text(header + "\n", encoding="utf-8")
    return tmp_path


def _trips() -> pl.DataFrame:
    return pl.read_csv(PERU / "trips.csv").sort("t_start")


def _at(epoch: int) -> datetime:
    return datetime.fromtimestamp(epoch, tz=UTC)


def _board(database_url, source, hora: datetime) -> dict:
    load(source, database_url, hora)  # la historia termina a esa hora y el replay queda ahí
    return TestClient(create_app(database_url)).get("/v1/freights").json()


def test_solo_los_viajes_terminados_suman_combustible_y_margen(database_url, peru_source):
    trips = _trips()
    middle = trips.row(len(trips) // 2, named=True)
    hora = _at(middle["t_start"] + 3600)  # ese viaje va en curso
    body = _board(database_url, peru_source, hora)
    assert body["provenance"] == ["synthetic_demo", "model_inferred"]
    fletes = {f["viaje_id"]: f for f in body["data"]["fletes"]}
    assert len(fletes) == len(trips)

    curso = fletes[middle["trip_id"]]
    assert curso["estado"] == "en_curso"
    assert curso["litros"] is None and curso["combustible_pen"] is None and curso["margen_pen"] is None
    assert curso["tarifa_pen"] > 0  # lo comercial sí se conoce de antemano

    hecho = [f for f in fletes.values() if f["estado"] == "finalizado"]
    futuros = [f for f in fletes.values() if f["estado"] == "programado"]
    assert hecho and futuros
    for f in hecho:
        assert f["litros"] > 0 and f["margen_pen"] == round(f["tarifa_pen"] - f["combustible_pen"], 2)
        assert 25 < f["l_100km"] < 80
    r = body["data"]["resumen"]
    assert r["fletes"] == len(hecho) and r["en_curso"] == 1 and r["programados"] == len(futuros)
    assert r["ingresos_pen"] == pytest.approx(sum(f["tarifa_pen"] for f in hecho))
    assert r["margen_pen"] == pytest.approx(r["ingresos_pen"] - r["combustible_pen"])
    assert r["detraccion_pen"] == pytest.approx(sum(f["detraccion_pen"] for f in hecho))


def test_un_flete_en_curso_se_finaliza_cuando_el_replay_pasa_su_llegada(database_url, peru_source):
    middle = _trips().row(len(_trips()) // 2, named=True)
    antes = _board(database_url, peru_source, _at(middle["t_start"] + 60))
    despues = _board(database_url, peru_source, _at(middle["t_end"] + 60))
    f0 = next(f for f in antes["data"]["fletes"] if f["viaje_id"] == middle["trip_id"])
    f1 = next(f for f in despues["data"]["fletes"] if f["viaje_id"] == middle["trip_id"])
    assert f0["estado"] == "en_curso" and f1["estado"] == "finalizado"
    assert f1["llegada"].startswith(_at(middle["t_end"]).strftime("%Y-%m-%dT%H:%M"))
    assert f1["litros"] == pytest.approx(middle["liters"])
    assert despues["data"]["resumen"]["fletes"] == antes["data"]["resumen"]["fletes"] + 1


def test_detraccion_del_4_por_ciento_y_agregados_por_corredor_cliente_vehiculo_y_dia(database_url, peru_source):
    body = _board(database_url, peru_source, _at(int(_trips()["t_end"].max()) + 60))
    d = body["data"]
    assert all(f["estado"] == "finalizado" for f in d["fletes"])
    for f in d["fletes"]:
        assert f["total_pen"] == pytest.approx(f["tarifa_pen"] + f["igv_pen"])
        assert f["detraccion_pen"] == pytest.approx(round(f["total_pen"] * 0.04, 2))
        assert f["gre_transportista"].startswith("V001-") and len(f["ruc_cliente"]) == 11
    assert [c["clave"] for c in d["por_corredor"]] == ["LIM-AQP"]
    assert {v["clave"] for v in d["por_vehiculo"]} == {"T03", "T07"}
    for grupo in ("por_corredor", "por_cliente", "por_vehiculo", "por_dia"):
        assert sum(g["fletes"] for g in d[grupo]) == d["resumen"]["fletes"]
        assert sum(g["ingresos_pen"] for g in d[grupo]) == pytest.approx(d["resumen"]["ingresos_pen"])


def test_la_telemetria_de_peru_se_declara_synthetic_demo(database_url, peru_source):
    _board(database_url, peru_source, _at(int(_trips()["t_start"].min()) + 600))
    body = TestClient(create_app(database_url)).get("/v1/fleet").json()
    assert body["provenance"] == ["synthetic_demo"]


def test_sin_fletes_el_tablero_esta_vacio(client):
    with psycopg.connect(client.app.state.database_url) as conn:
        conn.execute("TRUNCATE baselines, passes, telemetry_reading, telemetry_source, driver_reports, freights, trips, drivers, vehicles")
    d = client.get("/v1/freights").json()["data"]
    assert d["fletes"] == [] and d["resumen"]["fletes"] == 0 and d["resumen"]["margen_pct"] is None
