"""Integración: tar sintético -> viajes, pasadas, línea base y logística (con la lógica real de H3)."""
import polars as pl
import pytest

from fleetdata import pipeline
from fleetdata.pii import scan_dir


@pytest.fixture(scope="module")
def result(fake_fleet, tmp_path_factory):
    root = tmp_path_factory.mktemp("run")
    pipeline.run(fake_fleet["archive"], fake_fleet["alias_path"], root / "out", root / "fixtures",
                 demo=("T01", "T02"), verify=False, fixture_aliases=("T01", "T02"))
    return root


def test_viajes_entre_terminales_con_sentido(result):
    trips = pl.read_csv(result / "out" / "trips.csv")
    assert set(trips["alias"]) == {"T01", "T02"}
    assert set(trips["sentido"]) == {"ida", "vuelta"}
    assert trips["corridor"].n_unique() == 1
    assert (trips["t_end"] > trips["t_start"]).all()


def test_linea_base_con_toda_la_flota_y_celdas_res6(result):
    b = pl.read_csv(result / "out" / "baseline.csv")
    assert len(b) > 10
    # 5 vehículos con consumo 20, 22, 24, 26, 28 L/h a 80 km/h -> mediana 24 L/h = 30 L/100 km
    ida = b.filter(pl.col("sentido") == "ida")
    assert abs(ida["median_l_per_100km"].median() - 30.0) < 1.5
    assert (ida["n_vehicles"] == 5).all() and (b["n_passes"] >= 3).all()
    import h3
    assert {h3.get_resolution(c) for c in b["h3_cell"]} == {6}
    assert b["provenance"].unique().to_list() == ["model_inferred"]


def test_logistica_sintetica_demo(result):
    fr = pl.read_csv(result / "out" / "freights.csv")
    trips = pl.read_csv(result / "out" / "trips.csv")
    assert len(fr) == len(trips) and fr["trip_id"].n_unique() == len(trips)  # 1 flete por viaje
    assert fr["freight_id"][0] == "F-101"
    assert fr["provenance"].unique().to_list() == ["synthetic_demo"]


def test_la_salida_no_contiene_datos_personales(result, fake_fleet):
    forbidden = list(fake_fleet["alias_map"]) + [v["plate"] for v in fake_fleet["vehicles"]] + [v["imei"] for v in fake_fleet["vehicles"]]
    assert scan_dir(result, forbidden) == []
