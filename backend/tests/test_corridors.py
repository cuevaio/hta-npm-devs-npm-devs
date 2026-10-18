"""Geometría de los corredores para el mapa (ADR 0012)."""

import json

from fastapi.testclient import TestClient

from app.main import create_app
from scripts.load_demo_data import load
from tests.helpers import REPLAY_START

CURVA = [[-76.0, -12.0], [-75.99, -12.005], [-75.985, -12.012], [-75.99, -12.02]]


def test_los_corredores_cargados_se_sirven_con_su_via_y_procedencia_externa(database_url, source_dir):
    (source_dir / "corridors.json").write_text(json.dumps([
        {"corridor": "LIM-HYO", "via": "Carretera Central", "origin_terminal": "LIM", "dest_terminal": "HYO",
         "km": 307.3, "coords": CURVA},
    ]), encoding="utf-8")
    load(source_dir, database_url, REPLAY_START)
    body = TestClient(create_app(database_url)).get("/v1/corridors").json()
    assert body["provenance"] == ["external_enrichment"]
    [c] = body["data"]["corredores"]
    assert c["corredor"] == "LIM-HYO" and c["via"] == "Carretera Central"
    assert (c["origen"], c["destino"], c["largo_km"]) == ("LIM", "HYO", 307.3)
    assert c["coordenadas"] == CURVA  # en sentido ida, sin perder vértices


def test_sin_corridors_json_la_lista_queda_vacia_y_una_recarga_no_duplica(database_url, source_dir):
    (source_dir / "corridors.json").write_text(json.dumps([
        {"corridor": "AQP-JUL", "via": "PE-34A", "origin_terminal": "AQP", "dest_terminal": "JUL", "km": 249.3,
         "coords": CURVA},
    ]), encoding="utf-8")
    load(source_dir, database_url, REPLAY_START)
    load(source_dir, database_url, REPLAY_START)
    api = TestClient(create_app(database_url))
    assert len(api.get("/v1/corridors").json()["data"]["corredores"]) == 1
    (source_dir / "corridors.json").unlink()
    load(source_dir, database_url, REPLAY_START)
    assert api.get("/v1/corridors").json()["data"]["corredores"] == []
