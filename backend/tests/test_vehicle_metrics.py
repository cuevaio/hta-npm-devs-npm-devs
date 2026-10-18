"""Métricas históricas de un vehículo por día (hora de Lima) o por viaje, con un dataset de valores conocidos."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from scripts.load_demo_data import load
from tests.helpers import KEY

D = datetime(2020, 4, 1, 13, 0, tzinfo=UTC)  # 08:00 en Lima


def _ep(ts: datetime) -> int:
    return int(ts.timestamp())


def _csv(path, header: str, rows: list[str]) -> None:
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")


@pytest.fixture
def source(tmp_path):
    trips, freights, passes = [], [], []
    tarifas = {1: (3000, 1000), 2: (2000, 800), 3: (1500, 500)}
    for n in (1, 2, 3):
        start = D + timedelta(days=n - 1)
        trips.append(f"T07-V0{n},T07,X,ida,LIM,AQP,{_ep(start)},{_ep(start + timedelta(hours=4))},0,0,0,0")
        tarifa, costo = tarifas[n]
        freights.append(f"T07-V0{n},F-{n},T07,D-01,Cliente,Cemento,X,ida,LIM,AQP,{start:%Y-%m-%dT%H:%M:%SZ},synthetic_demo,{tarifa},{costo}")
    trips.append(f"T03-V01,T03,X,ida,LIM,AQP,{_ep(D)},{_ep(D + timedelta(hours=4))},0,0,0,0")
    freights.append(f"T03-V01,F-9,T03,D-01,Cliente,Cemento,X,ida,LIM,AQP,{D:%Y-%m-%dT%H:%M:%SZ},synthetic_demo,9999,1")

    def pasada(trip, cell, start, km, liters):
        passes.append(f"{trip},T07,X,ida,{cell},{_ep(start)},{_ep(start + timedelta(minutes=10))},1,{km},{liters},{liters / km * 100},true")

    pasada("T07-V01", "A", D + timedelta(minutes=5), 10, 4)    # en la mediana
    pasada("T07-V01", "B", D + timedelta(minutes=15), 10, 6)   # sobreconsumo: +2 L
    pasada("T07-V01", "C", D + timedelta(minutes=25), 10, 5)   # sin línea base
    pasada("T07-V02", "A", D + timedelta(days=1, minutes=10), 10, 5)  # sobreconsumo: +1 L
    pasada("T07-V03", "A", D + timedelta(days=2, minutes=10), 10, 4)

    tel = []

    def lectura(ts, speed, rpm):
        tel.append(f"T07,{ts:%Y-%m-%dT%H:%M:%SZ},-12.0,-77.0,{speed},{rpm},10,1000,1000,{str(rpm > 0).lower()},synthetic_demo")

    for i in range(541):  # 1 h en movimiento, 30 min en ralentí y el motor se apaga, dentro de T07-V01
        lectura(D + timedelta(seconds=10 * i), 60 if i < 360 else 0, 1400 if i < 360 else 700 if i < 540 else 0)
    noche = datetime(2020, 4, 2, 3, 0, tzinfo=UTC)  # 22:00 del 1 de abril en Lima, sin viaje
    for i in range(91):
        lectura(noche + timedelta(seconds=10 * i), 0, 700 if i < 90 else 0)

    _csv(tmp_path / "trips.csv", "trip_id,alias,corridor,sentido,origin_terminal,dest_terminal,t_start,t_end,"
         "origin_lat,origin_lon,dest_lat,dest_lon", trips)
    _csv(tmp_path / "freights.csv", "trip_id,freight_id,alias,driver_id,client,cargo,corridor,sentido,"
         "origin_terminal,dest_terminal,planned_departure,provenance,tarifa_pen,fuel_cost_pen", freights)
    _csv(tmp_path / "passes_demo.csv", "trip_id,alias,corridor,sentido,h3_cell,t_start,t_end,day,km,liters,"
         "l_per_100km,in_baseline", passes)
    _csv(tmp_path / "baseline.csv", "corridor,sentido,h3_cell,n_passes,n_vehicles,median_l_per_100km,"
         "p90_l_per_100km,median_liters,p90_liters,median_km,provenance",
         ["X,ida,A,5,3,40,45,4,4.5,10,model_inferred", "X,ida,B,5,3,40,50,4,5,10,model_inferred"])
    _csv(tmp_path / "telemetry.csv", "alias,event_time,lat,lon,speed_kmh,rpm,fuel_rate_lph,fuel_total_l,"
         "odometer_km,engine_on,provenance", tel)
    _csv(tmp_path / "drivers.csv", "driver_id,name,provenance", ["D-01,Hugo Montalvo,synthetic_demo"])
    _csv(tmp_path / "driver_reports.csv", "report_id,trip_id,driver_id,reported_at,text,provenance",
         [f"R-1,T07-V01,D-01,{D:%Y-%m-%dT%H:%M:%SZ},ok,human_reported"])
    return tmp_path


def _api(database_url, source, hora: datetime) -> TestClient:
    load(source, database_url, hora)
    return TestClient(create_app(database_url, api_key="secreta"))


FIN = datetime(2020, 4, 4, 0, 0, tzinfo=UTC)  # 3 de abril, 19:00 en Lima: todo ya ocurrió


def test_por_dia_en_hora_de_lima_con_consumo_frente_a_pares_ralenti_y_fletes(database_url, source):
    body = _api(database_url, source, FIN).get("/v1/vehicles/T07/metrics").json()
    assert body["provenance"] == ["synthetic_demo", "model_inferred"]
    data = body["data"]
    assert (data["alias"], data["agrupar_por"], data["desde"], data["hasta"]) == ("T07", "dia", "2020-04-01", "2020-04-03")
    dias = {f["clave"]: f for f in data["filas"]}
    assert list(dias) == ["2020-04-01", "2020-04-02", "2020-04-03"]

    d1 = dias["2020-04-01"]
    assert d1["viajes_finalizados"] == 1 and d1["km"] == 30 and d1["litros"] == 15 and d1["l_100km"] == 50
    assert (d1["tramos"], d1["tramos_con_linea_base"], d1["tramos_sobreconsumo"]) == (3, 2, 1)
    assert d1["litros_linea_base"] == 8 and d1["exceso_l"] == 2 and d1["vs_pares_pct"] == 25
    assert d1["horas_en_movimiento"] == 1.0
    assert d1["ralenti_h"] == 0.75  # 30 min del viaje + 15 min de la noche, que en Lima sigue siendo el día 1
    assert (d1["ingresos_pen"], d1["combustible_pen"], d1["margen_pen"]) == (3000, 1000, 2000)
    assert d1["corredor"] is None and d1["sentido"] is None

    assert dias["2020-04-02"]["exceso_l"] == 1 and dias["2020-04-02"]["ralenti_h"] == 0
    assert dias["2020-04-03"]["vs_pares_pct"] == 0 and dias["2020-04-03"]["tramos_sobreconsumo"] == 0

    total = data["resumen"]
    assert total["clave"] == "total" and total["viajes_finalizados"] == 3
    assert total["km"] == 50 and total["litros"] == 24 and total["exceso_l"] == 3
    assert total["vs_pares_pct"] == pytest.approx(18.8, abs=0.05)
    assert total["ingresos_pen"] == 6500 and total["margen_pen"] == 4200


def test_por_viaje_el_ralenti_fuera_de_un_viaje_no_se_le_atribuye(database_url, source):
    data = _api(database_url, source, FIN).get("/v1/vehicles/T07/metrics?agrupar_por=viaje").json()["data"]
    viajes = {f["clave"]: f for f in data["filas"]}
    assert list(viajes) == ["T07-V01", "T07-V02", "T07-V03"]
    v1 = viajes["T07-V01"]
    assert (v1["corredor"], v1["sentido"]) == ("X", "ida")
    assert v1["ralenti_h"] == 0.5 and v1["horas_en_movimiento"] == 1.0 and v1["exceso_l"] == 2
    assert v1["margen_pen"] == 2000


def test_nunca_revela_lo_que_el_replay_no_reprodujo(database_url, source):
    hora = D + timedelta(days=1, hours=2)  # T07-V02 en curso; T07-V03 todavía no empieza
    data = _api(database_url, source, hora).get("/v1/vehicles/T07/metrics").json()["data"]
    assert data["hasta"] == "2020-04-02"
    dias = {f["clave"]: f for f in data["filas"]}
    assert list(dias) == ["2020-04-01", "2020-04-02"]
    d2 = dias["2020-04-02"]
    assert d2["km"] == 10  # su pasada ya terminó
    assert d2["viajes_finalizados"] == 0 and d2["ingresos_pen"] == 0  # el viaje aún no llega
    assert data["resumen"]["viajes_finalizados"] == 1


def test_rango_de_fechas_y_dias_sin_actividad_en_cero(database_url, source):
    api = _api(database_url, source, FIN)
    solo = api.get("/v1/vehicles/T07/metrics?desde=2020-04-02&hasta=2020-04-02").json()["data"]
    assert [f["clave"] for f in solo["filas"]] == ["2020-04-02"] and solo["resumen"]["km"] == 10

    antes = api.get("/v1/vehicles/T07/metrics?desde=2020-03-30&hasta=2020-04-01").json()["data"]
    filas = {f["clave"]: f for f in antes["filas"]}
    assert list(filas) == ["2020-03-30", "2020-03-31", "2020-04-01"]
    assert filas["2020-03-30"]["km"] == 0 and filas["2020-03-30"]["l_100km"] is None


def test_errores_y_tool_con_api_key(database_url, source):
    api = _api(database_url, source, FIN)
    assert api.get("/v1/vehicles/T99/metrics").status_code == 404
    assert api.get("/v1/vehicles/T07/metrics?desde=2020-04-03&hasta=2020-04-01").status_code == 422
    assert api.get("/v1/vehicles/T07/metrics?agrupar_por=semana").status_code == 422

    assert api.get("/v1/tools/get_vehicle_metrics?alias=T07").status_code == 401
    tool = api.get("/v1/tools/get_vehicle_metrics?alias=T07&agrupar_por=viaje", headers=KEY)
    assert tool.status_code == 200
    assert [f["clave"] for f in tool.json()["data"]["filas"]] == ["T07-V01", "T07-V02", "T07-V03"]
