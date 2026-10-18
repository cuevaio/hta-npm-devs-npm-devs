import polars as pl

from fleetdata.synthetic import generate


def _trips():
    return pl.DataFrame({
        "trip_id": ["T04-V01", "T03-V01", "T04-V02"], "alias": ["T04", "T03", "T04"],
        "corridor": ["K01-K02"] * 3, "sentido": ["ida", "ida", "vuelta"],
        "origin_terminal": ["K01", "K01", "K02"], "dest_terminal": ["K02", "K02", "K01"],
        "t_start": [1586275200 + 3600 * i * 30 for i in range(3)], "t_end": [1586275200 + 3600 * (i * 30 + 28) for i in range(3)],
    })


def test_misma_semilla_misma_salida():
    a, b = generate(_trips(), seed=1), generate(_trips(), seed=1)
    assert all(a[k].equals(b[k]) for k in a)
    c = generate(_trips(), seed=2)
    assert not a["freights"].equals(c["freights"])


def test_fletes_uno_a_uno_con_viaje_y_procedencia_synthetic_demo():
    s = generate(_trips())
    assert s["freights"]["freight_id"].to_list() == ["F-101", "F-102", "F-103"]
    assert s["freights"]["trip_id"].n_unique() == 3
    for df in s.values():
        assert df["provenance"].unique().to_list() == ["synthetic_demo"]


def test_reporte_guionado_se_asocia_al_viaje_que_lo_cubre():
    # T04: ralentí guionado el 2020-04-07 19:50 local (UTC+8) = 11:50 UTC
    t0 = 1586260000  # 2020-04-07 11:46:40 UTC
    trips = _trips().with_columns(pl.when(pl.col("trip_id") == "T04-V01").then(t0 + 600).otherwise(pl.col("t_start")).alias("t_start"),
                                  pl.when(pl.col("trip_id") == "T04-V01").then(t0 + 86400).otherwise(pl.col("t_end")).alias("t_end"))
    r = generate(trips)["driver_reports"]
    assert "T04-V01" in r.filter(pl.col("text").str.contains("calentando"))["trip_id"].to_list()
