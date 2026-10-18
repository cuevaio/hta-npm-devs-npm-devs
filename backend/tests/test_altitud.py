"""La altitud de la última posición conocida llega al estado del vehículo y a la flota (ADR 0012)."""

from datetime import datetime

import polars as pl
from fastapi.testclient import TestClient

from app.main import create_app
from scripts.load_demo_data import load
from tests.helpers import KEY, REPLAY_START

CONTROL = "/v1/tools/control_replay"
SEEK = "2020-04-03T20:00:00Z"  # después del inicio del replay: las lecturas llegan copiadas por el motor


def _con_altitud(source_dir) -> pl.DataFrame:
    """Agrega a la telemetría del fixture una altitud distinta por lectura, para saber cuál se devolvió."""
    path = source_dir / "telemetry.csv"
    df = pl.read_csv(path).with_columns((pl.col("odometer_km") % 4000).round(1).alias("alt_m"))
    df.write_csv(path)
    return df


def _api(database_url, clock) -> TestClient:
    return TestClient(create_app(database_url, api_key="secreta", clock=clock))


def _altitud_esperada(df: pl.DataFrame, alias: str, hora_evento: str) -> float:
    hora = datetime.fromisoformat(hora_evento)
    ultima = (
        df.with_columns(pl.col("event_time").str.to_datetime(time_zone="UTC"))
        .filter((pl.col("alias") == alias) & (pl.col("event_time") <= hora) & pl.col("lat").is_not_null())
        .sort("event_time")
        .tail(1)
    )
    return ultima["alt_m"][0]


def test_el_estado_del_vehiculo_trae_la_altitud_de_su_ultima_posicion(database_url, source_dir, clock):
    df = _con_altitud(source_dir)
    load(source_dir, database_url, REPLAY_START)
    api = _api(database_url, clock)
    api.post(CONTROL, headers=KEY, json={"action": "seek", "to_event_time": SEEK})

    data = api.get("/v1/tools/get_vehicle_status", params={"alias": "T07"}, headers=KEY).json()["data"]

    assert data["altitud_m"] == _altitud_esperada(df, "T07", data["hora_evento"])


def test_la_vista_de_flota_trae_la_altitud_de_cada_vehiculo(database_url, source_dir, clock):
    df = _con_altitud(source_dir)
    load(source_dir, database_url, REPLAY_START)
    api = _api(database_url, clock)
    api.post(CONTROL, headers=KEY, json={"action": "seek", "to_event_time": SEEK})

    vehiculos = api.get("/v1/fleet").json()["data"]["vehiculos"]

    assert {v["alias"] for v in vehiculos} == {"T03", "T07"}
    for v in vehiculos:
        assert v["altitud_m"] == _altitud_esperada(df, v["alias"], v["hora_evento"])


def test_sin_altitud_en_la_fuente_la_api_la_devuelve_nula(api):
    """El pipeline de FEAD no trae altitud: la carga funciona igual y el dato viaja como null."""
    api.post(CONTROL, headers=KEY, json={"action": "seek", "to_event_time": SEEK})

    data = api.get("/v1/vehicles/T07").json()["data"]

    assert data["altitud_m"] is None
