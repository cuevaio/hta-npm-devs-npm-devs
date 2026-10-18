import polars as pl

from fleetdata.baseline import compute_baseline


def _passes(rows):
    return pl.DataFrame(rows, orient="row", schema={"corridor": pl.String, "sentido": pl.String, "h3_cell": pl.String, "alias": pl.String,
                                      "day": pl.Int64, "l_per_100km": pl.Float64, "liters": pl.Float64, "km": pl.Float64})


def row(cell, sentido, alias, day, l100, km=6.0):
    return ("K01-K02", sentido, cell, alias, day, l100, l100 * km / 100, km)


def test_mediana_p90_y_n_por_celda_y_sentido():
    p = _passes([row("c1", "ida", "T01", 1, 30), row("c1", "ida", "T02", 2, 40), row("c1", "ida", "T03", 3, 50),
                 row("c1", "ida", "T04", 4, 60), row("c1", "vuelta", "T01", 1, 90)] * 1)
    b = compute_baseline(p)
    ida = b.filter(pl.col("sentido") == "ida").row(0, named=True)
    assert ida["n_passes"] == 4 and ida["n_vehicles"] == 4
    assert ida["median_l_per_100km"] == 45.0
    assert abs(ida["p90_l_per_100km"] - 57.0) < 1e-9
    assert b.filter(pl.col("sentido") == "vuelta").is_empty()  # el otro sentido no mezcla ni llega a 3


def test_tramo_con_dos_pasadas_no_tiene_linea_base():
    p = _passes([row("c1", "ida", "T01", 1, 30), row("c1", "ida", "T02", 2, 40),
                 row("c2", "ida", "T01", 1, 30), row("c2", "ida", "T02", 2, 40), row("c2", "ida", "T03", 3, 50)])
    assert compute_baseline(p)["h3_cell"].to_list() == ["c2"]


def test_solo_cuentan_los_dias_1_a_12():
    p = _passes([row("c1", "ida", "T01", 1, 30), row("c1", "ida", "T02", 12, 40),
                 row("c1", "ida", "T03", 13, 500), row("c1", "ida", "T04", 19, 500)])
    assert compute_baseline(p).is_empty()  # 2 pasadas en el periodo
    p2 = p.vstack(_passes([row("c1", "ida", "T05", 7, 50)]))
    b = compute_baseline(p2)
    assert b["n_passes"].to_list() == [3] and b["median_l_per_100km"].to_list() == [40.0]
