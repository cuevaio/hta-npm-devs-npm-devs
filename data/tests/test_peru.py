"""Flota sintética de Perú (ADR 0012): rutas reales, física creíble, casos de la demo y fletes peruanos."""
import polars as pl
import pytest

from fleetdata import peru
from fleetdata.pii import scan_dir
from fleetdata.rutas import CORREDORES, cargar
from fleetdata.synthetic import comercial, ruc_ficticio

PERU = {"lat": (-18.5, -3.3), "lon": (-81.5, -68.5)}


@pytest.fixture(scope="module")
def out(tmp_path_factory):
    root = tmp_path_factory.mktemp("peru")
    peru.run(root / "out", root / "fixtures")
    return root


def _read(out, name):
    return pl.read_csv(out / "out" / name)


def test_rutas_versionadas_de_los_cuatro_corredores():
    rutas = cargar()
    assert set(rutas) == set(CORREDORES)
    assert 950 < rutas["LIM-AQP"].largo_km < 1100
    assert rutas["LIM-HYO"].alt_m.max() > 4500  # Ticlio


def test_la_telemetria_esta_en_peru_y_es_synthetic_demo(out):
    for alias in peru.DEMO_ALIASES:
        df = pl.read_parquet(out / "out" / "telemetry" / f"{alias}.parquet")
        assert df["lat"].min() > PERU["lat"][0] and df["lat"].max() < PERU["lat"][1]
        assert df["lon"].min() > PERU["lon"][0] and df["lon"].max() < PERU["lon"][1]
        assert df["provenance"].unique().to_list() == ["synthetic_demo"]
        assert df["event_time"].is_sorted()
        assert df["fuel_total_l"].is_sorted() and df["odometer_km"].is_sorted()


def test_cada_lectura_trae_la_altitud_real_de_su_punto_de_la_ruta(out):
    for alias in peru.DEMO_ALIASES:
        df = pl.read_parquet(out / "out" / "telemetry" / f"{alias}.parquet")
        assert df["alt_m"].null_count() == 0
        assert 0 <= df["alt_m"].min() and df["alt_m"].max() < 5000  # de la costa a Ticlio (4 818 msnm)
    t22 = pl.read_parquet(out / "out" / "telemetry" / "T22.parquet")  # LIM-HYO cruza Ticlio
    assert t22["alt_m"].max() > 4500
    t28 = pl.read_parquet(out / "out" / "telemetry" / "T28.parquet")  # AQP-JUL llega al altiplano
    assert t28["alt_m"].max() > 3800


def test_consumo_creible_y_la_sierra_gasta_mas_de_subida(out):
    trips = _read(out, "trips.csv")
    llano = trips.filter(pl.col("corridor") == "LIM-PIU")["l_per_100km"].median()
    assert 28 < llano < 42
    hyo = trips.filter(pl.col("corridor") == "LIM-HYO").group_by("sentido").agg(pl.col("l_per_100km").median())
    l = dict(zip(hyo["sentido"], hyo["l_per_100km"]))
    assert l["ida"] > 1.3 * l["vuelta"]


def test_linea_base_por_tramo_con_pares(out):
    b = _read(out, "baseline.csv")
    aqp = b.filter(pl.col("corridor") == "LIM-AQP")
    assert len(aqp) > 100 and aqp["n_vehicles"].median() >= 5
    assert b["provenance"].unique().to_list() == ["model_inferred"]


def test_t07_gasta_mas_que_sus_pares_en_el_replay(out):
    p = _read(out, "passes_demo.csv").filter(pl.col("corridor") == "LIM-AQP")
    b = _read(out, "baseline.csv")
    j = p.join(b, on=["corridor", "sentido", "h3_cell"]).with_columns(
        (pl.col("l_per_100km") / pl.col("median_l_per_100km")).alias("r"))
    r = {(a, base): v for a, base, v in j.group_by("alias", "in_baseline").agg(pl.col("r").median()).iter_rows()}
    assert r[("T07", False)] > 1.15 and r[("T07", True)] < 1.05
    assert r[("T03", False)] < 1.03


def _paradas(df: pl.DataFrame, desde_s: int, min_s: int):
    """Corridas con velocidad cero (motor encendido) de al menos min_s."""
    d = df.filter(pl.col("event_time").dt.epoch("s") >= desde_s).with_columns(
        (pl.col("speed_kmh") < 1).alias("q"))
    d = d.with_columns((pl.col("q") != pl.col("q").shift()).cum_sum().alias("g"))
    g = d.filter("q").group_by("g").agg(pl.col("event_time").min().alias("t0"), pl.col("event_time").max().alias("t1"))
    return g.filter((pl.col("t1") - pl.col("t0")).dt.total_seconds() >= min_s)


def test_t04_ralenti_largo_en_el_replay_con_reporte(out):
    df = pl.read_parquet(out / "out" / "telemetry" / "T04.parquet")
    assert len(_paradas(df, peru.REPLAY_DESDE, 4 * 3600)) >= 1
    r = _read(out, "driver_reports.csv")
    assert r.filter(pl.col("trip_id").str.starts_with("T04") & pl.col("text").str.contains("motor prendido")).height == 1


def test_t28_parada_sin_explicar_en_el_replay(out):
    trips = _read(out, "trips.csv").filter((pl.col("alias") == "T28") & (pl.col("t_start") >= peru.REPLAY_DESDE)).sort("t_start")
    primero = trips.row(0, named=True)
    # el motor se apaga en la parada: hay un hueco de más de 2 h en mitad del viaje
    df = pl.read_parquet(out / "out" / "telemetry" / "T28.parquet").filter(
        pl.col("event_time").dt.epoch("s").is_between(primero["t_start"], primero["t_end"]))
    huecos = df["event_time"].diff().dt.total_seconds().drop_nulls()
    assert huecos.max() >= 2 * 3600
    assert primero["trip_id"] not in _read(out, "driver_reports.csv")["trip_id"].to_list()


def test_fletes_peruanos_uno_a_uno(out):
    fr, trips = _read(out, "freights.csv"), _read(out, "trips.csv")
    assert len(fr) == len(trips) and fr["trip_id"].n_unique() == len(trips)
    assert fr["provenance"].unique().to_list() == ["synthetic_demo"]
    assert fr["gre_transportista"].str.starts_with("V001-").all()
    assert (fr["fuel_cost_pen"] > 0).all() and (fr["tarifa_pen"] > fr["fuel_cost_pen"]).all()


def test_reglas_comerciales():
    c = comercial("LIM-AQP", 28.0, 1000.0, 300.0)
    assert c["tarifa_pen"] == 4760.0 and c["igv_pen"] == round(4760 * 0.18, 2)
    assert c["detraccion_pen"] == round(c["total_pen"] * 0.04, 2)
    assert comercial("LIM-AQP", 1.0, 100.0, None)["detraccion_pen"] == 0.0  # 10 t mínimo x 100 km = S/ 170 + IGV


def test_ruc_ficticio_con_digito_verificador_invalido():
    import random
    rng = random.Random(1)
    for _ in range(50):
        ruc = ruc_ficticio(rng)
        base = ruc[:10]
        resto = sum(int(d) * w for d, w in zip(base, (5, 4, 3, 2, 7, 6, 5, 4, 3, 2))) % 11
        assert len(ruc) == 11 and ruc.startswith("20") and int(ruc[10]) != (11 - resto) % 10


def test_determinista(out, tmp_path):
    peru.run(tmp_path / "out", None)
    assert pl.read_csv(tmp_path / "out" / "trips.csv").equals(_read(out, "trips.csv"))


def test_sin_datos_personales(out):
    assert scan_dir(out, []) == []


def _distancia_a_la_via_m(lat, lon, ruta) -> "np.ndarray":
    """Distancia de cada punto a la polilínea de la vía (proyección local en metros, ventana por cercanía)."""
    import numpy as np

    _, la, lo = ruta._linea()
    k = np.cos(np.radians(la.mean()))
    vx, vy = lo * 111_195 * k, la * 111_195
    px, py = lon * 111_195 * k, lat * 111_195
    ax, ay, dx, dy = vx[:-1], vy[:-1], np.diff(vx), np.diff(vy)
    l2 = np.maximum(dx * dx + dy * dy, 1e-9)
    out = np.empty(len(px))
    for i, (x, y) in enumerate(zip(px, py)):  # distancia exacta a todos los segmentos
        t = np.clip(((x - ax) * dx + (y - ay) * dy) / l2, 0, 1)
        out[i] = np.sqrt(((x - ax - t * dx) ** 2 + (y - ay - t * dy) ** 2).min())
    return out


def test_en_marcha_el_camion_va_sobre_la_pista_real(out):
    """Con zoom alto el camión no debe pisar casas: p95 a menos de 5 m de la vía, nunca a más de 12 m."""
    import numpy as np

    rutas = cargar()
    trips = _read(out, "trips.csv")
    for alias in ("T22", "T03"):  # Carretera Central (serpentines) y Panamericana Sur
        df = pl.read_parquet(out / "out" / "telemetry" / f"{alias}.parquet").filter(pl.col("speed_kmh") > 5)
        corredor = trips.filter(pl.col("alias") == alias)["corridor"][0]
        muestra = df.gather_every(97)
        d = _distancia_a_la_via_m(muestra["lat"].to_numpy(), muestra["lon"].to_numpy(), rutas[corredor])
        assert np.percentile(d, 95) < 5 and d.max() < 12, (alias, np.percentile(d, 95), d.max())


def test_la_parada_en_ralenti_queda_en_la_berma_derecha():
    import numpy as np

    ruta = cargar()["LIM-AQP"]
    km = 500.0
    lat, lon = ruta.berma(km)
    d = _distancia_a_la_via_m(np.array([lat]), np.array([lon]), ruta)[0]
    assert 4 < d < 8
    # a la derecha: el producto vectorial (avance x desplazamiento) es negativo en el plano lon/lat
    la, lo = ruta.punto(np.array([km - 0.05, km, km + 0.05]))
    ax, ay = lo[2] - lo[0], la[2] - la[0]
    assert ax * (lat - la[1]) - ay * (lon - lo[1]) < 0
    lat_v, lon_v = ruta.invertida().berma(ruta.largo_km - km)
    assert np.hypot(lat_v - lat, lon_v - lon) > 5e-5  # en vuelta queda del otro lado


def test_corredores_para_el_mapa(out):
    import json

    cs = json.loads((out / "out" / "corridors.json").read_text())
    assert {c["corridor"] for c in cs} == set(CORREDORES)
    lim_hyo = next(c for c in cs if c["corridor"] == "LIM-HYO")
    assert len(lim_hyo["coords"]) > 2000 and 300 < lim_hyo["km"] < 320
