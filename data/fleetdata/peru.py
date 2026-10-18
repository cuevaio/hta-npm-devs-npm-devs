"""Flota sintética en corredores de Perú: telemetría, viajes, línea base y logística (ADR 0012).

    uv run python -m fleetdata.peru --out out

Todo es `synthetic_demo` salvo la línea base (`model_inferred`): 28 tractocamiones (T01…T28) recorren
cuatro corredores reales durante 19 días con el modelo de `fisica.py`. La salida tiene el mismo formato
que la del pipeline de FEAD, así que el backend la carga igual. Es determinista: misma semilla, misma
salida.

Los días de la flota mantienen el corte del replay del backend (16:00 UTC, días 1-12 de historia y
13-19 de replay) para no mover el contrato.
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import polars as pl

from . import baseline as bl
from . import synthetic as syn
from . import trips as tp
from .fisica import Camion, Manejo, perfil
from .fixture import make_fixture
from .rutas import CORREDORES, TERMINALES, Ruta, cargar

PROVENANCE = "synthetic_demo"
SEED = 2026
INICIO = int(datetime(2020, 3, 31, 16, tzinfo=timezone.utc).timestamp())  # día 1 de la flota
N_DIAS = 19
FIN = INICIO + N_DIAS * 86400
REPLAY_DESDE = INICIO + bl.BASELINE_LAST_DAY * 86400
PASO_S = 2
DEMO_ALIASES = ("T03", "T04", "T07", "T22", "T09", "T28")
DEFAULT_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

FLOTA = {
    "LIM-AQP": ["T01", "T02", "T03", "T04", "T05", "T06", "T07", "T08", "T10", "T11"],
    "LIM-HYO": ["T12", "T13", "T14", "T15", "T16", "T17", "T22"],
    "LIM-PIU": ["T09", "T18", "T19", "T20", "T21", "T23"],
    "AQP-JUL": ["T24", "T25", "T26", "T27", "T28"],
}
# Carga típica por corredor y sentido (t): la ida desde Lima sale más cargada.
CARGA_T = {("LIM-AQP", "ida"): (22, 30), ("LIM-AQP", "vuelta"): (12, 26), ("LIM-HYO", "ida"): (18, 28),
           ("LIM-HYO", "vuelta"): (10, 24), ("LIM-PIU", "ida"): (20, 30), ("LIM-PIU", "vuelta"): (14, 28),
           ("AQP-JUL", "ida"): (16, 26), ("AQP-JUL", "vuelta"): (8, 20)}
DESCANSO_CADA_S = 4.5 * 3600
DORMIR_SI_MAS_DE_S = 12 * 3600


@dataclass
class Perfil:
    """Rasgos de un vehículo y su conductor habitual que el generador respeta."""

    camion: Camion = field(default_factory=Camion)
    manejo: Manejo = field(default_factory=Manejo)
    ralenti_en_paradas: bool = False  # deja el motor encendido al parar
    calentamiento_s: int = 15 * 60
    condicion_replay: float | None = None  # el vehículo empieza a gastar más en los días del replay


@dataclass(frozen=True)
class Guion:
    """Caso de la demo: qué le pasa a un vehículo en su n-ésimo viaje del replay y qué reporta."""

    alias: str
    viaje_replay: int  # 1 = primer viaje que arranca en los días 13-19
    tipo: str  # parada_sin_explicar | parada_explicada | espera_terminal | carga_completa
    reporte: str | None = None
    km_frac: float = 0.5
    dur_s: int = 0


GUIONES = [
    # Ralentí: el conductor de T04 duerme con el motor encendido.
    Guion("T04", 1, "parada_explicada", "Paré a dormir en Nasca, dejé el motor prendido por el frío de la madrugada. "
          "Salgo en unas horas.", km_frac=0.45, dur_s=5 * 3600),
    # Ralentí explicado en el terminal antes de salir.
    Guion("T03", 1, "espera_terminal", "Esperando que terminen de cargar en el terminal de Lima, dejé el motor en "
          "marcha.", dur_s=70 * 60),
    # Subida a Ticlio con la carga al máximo: consumo alto pero explicado.
    Guion("T22", 1, "carga_completa", "Subiendo a Ticlio con carga completa, voy lento y con el acelerador a fondo.",
          km_frac=0.33),
    # Cuello de botella: parada larga sin explicar en el altiplano.
    Guion("T28", 1, "parada_sin_explicar", None, km_frac=0.55, dur_s=2 * 3600 + 15 * 60),
    Guion("T28", 2, "parada_explicada", "Granizada y neblina en Santa Lucía, espero que despeje para seguir.",
          km_frac=0.5, dur_s=80 * 60),
    Guion("T09", 1, "parada_explicada", "Tráfico detenido por obras en la Panamericana Norte, pasada Chiclayo.",
          km_frac=0.8, dur_s=50 * 60),
]


def perfiles(rng: random.Random) -> dict[str, Perfil]:
    out = {}
    for corredor, aliases in FLOTA.items():
        for alias in aliases:
            camion = Camion(p_max_kw=rng.choice([300, 320, 340]), cda_m2=rng.uniform(5.5, 6.1),
                            condicion=rng.gauss(1.0, 0.03))
            manejo = Manejo(v_crucero_kmh=rng.uniform(76, 86), acel_ms2=rng.uniform(0.25, 0.45))
            out[alias] = Perfil(camion, manejo, ralenti_en_paradas=rng.random() < 0.15)
    out["T04"].ralenti_en_paradas = True
    # T07 empieza a rendir peor en el replay: el sobreconsumo que la demo detecta (sin reporte que lo explique).
    out["T07"].camion = replace(out["T07"].camion, condicion=1.0)
    out["T07"].condicion_replay = 1.28
    out["T03"].camion = replace(out["T03"].camion, condicion=0.98)
    return out


@dataclass
class Tramo:
    """Trozo continuo de la línea de tiempo de un vehículo con el motor encendido."""

    t: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    alt: np.ndarray  # msnm, SRTM de la ruta (rutas_peru.json)
    v_kmh: np.ndarray
    lph: np.ndarray
    carga: np.ndarray


def _quieto(t0: float, dur: float, lat: float, lon: float, alt: float, camion: Camion) -> Tramo:
    t = np.arange(t0, t0 + dur, PASO_S, dtype=float)
    z = np.zeros(len(t))
    return Tramo(t, z + lat, z + lon, z + alt, z, z + camion.ralenti_lph * camion.condicion, z)


def simular_viaje(ruta: Ruta, masa_t: float, pf: Perfil, t0: float, paradas, lentos):
    """Viaje continuo con paradas [(km, duración_s, ralentí)]; devuelve los tramos con motor y la llegada."""
    vm, lph, carga, dt = perfil(ruta, masa_t, pf.camion, pf.manejo, [p[0] for p in paradas], lentos)
    km_mid = (ruta.km[:-1] + ruta.km[1:]) / 2
    manejo_t = np.concatenate(([0.0], np.cumsum(dt)))  # hora de cada punto de la malla sin paradas
    corte = [0] + [min(int(np.searchsorted(ruta.km, p[0])), len(ruta.km) - 1) for p in paradas] + [len(ruta.km) - 1]
    tramos: list[Tramo] = []
    retraso = t0
    for n, (a, b) in enumerate(zip(corte[:-1], corte[1:])):
        tb = manejo_t[a : b + 1] + retraso
        if b > a:
            ts = np.arange(tb[0], tb[-1], PASO_S)
            km = np.interp(ts, tb, ruta.km[a : b + 1])
            i = np.clip(np.searchsorted(km_mid, km), 0, len(vm) - 1)
            tramos.append(Tramo(ts, np.interp(km, ruta.km, ruta.lat), np.interp(km, ruta.km, ruta.lon),
                                np.interp(km, ruta.km, ruta.alt_m), np.interp(km, km_mid, vm) * 3.6, lph[i], carga[i]))
        if n < len(paradas):
            _, dur, ralenti = paradas[n]
            if ralenti:  # al costado de la vía, unos 30 m
                tramos.append(_quieto(tb[-1], dur, ruta.lat[b] + 0.00027, ruta.lon[b], ruta.alt_m[b], pf.camion))
            retraso += dur
    return tramos, float(manejo_t[-1] + retraso)


def _ruido(tr: Tramo, rng: np.random.Generator) -> Tramo:
    n = len(tr.t)
    mov = tr.v_kmh > 0.5
    # la altitud no lleva ruido: no consume números del generador y el resto de la salida no cambia
    return Tramo(tr.t, tr.lat + rng.normal(0, 3e-5, n) * mov, tr.lon + rng.normal(0, 3e-5, n) * mov, tr.alt,
                 np.maximum(0, tr.v_kmh + rng.normal(0, 0.6, n) * mov),
                 np.maximum(0.2, tr.lph * rng.normal(1, 0.04, n)), tr.carga)


def _frame(alias: str, tramos: list[Tramo], rng: np.random.Generator, odo0: float, fuel0: float) -> pl.DataFrame:
    tramos = [_ruido(t, rng) for t in tramos if len(t.t)]
    t = np.concatenate([x.t for x in tramos])
    orden = np.argsort(t, kind="stable")
    t = t[orden]
    col = {k: np.concatenate([getattr(x, k) for x in tramos])[orden] for k in ("lat", "lon", "alt", "v_kmh", "lph", "carga")}
    keep = (t >= INICIO) & (t < FIN)
    dt = np.minimum(np.diff(t, prepend=t[0]), PASO_S)
    fuel_total = fuel0 + np.cumsum(col["lph"] * dt / 3600)
    odo = odo0 + np.cumsum(col["v_kmh"] * dt / 3600)
    mov = col["v_kmh"] > 0.5
    rpm = np.where(mov, 1000 + 520 * col["carga"] + rng.normal(0, 40, len(t)), 650 + rng.normal(0, 15, len(t)))
    return pl.DataFrame({
        "alias": alias,
        "event_time": (t[keep] * 1e6).astype(np.int64),
        "lat": np.round(col["lat"][keep], 6), "lon": np.round(col["lon"][keep], 6),
        "alt_m": np.round(col["alt"][keep], 1),
        "speed_kmh": np.round(col["v_kmh"][keep], 1), "rpm": np.round(rpm[keep]),
        "fuel_rate_lph": np.round(col["lph"][keep], 2), "fuel_total_l": np.round(fuel_total[keep], 2),
        "odometer_km": np.round(odo[keep], 2), "engine_on": True, "provenance": PROVENANCE,
    }).with_columns(pl.col("event_time").cast(pl.Datetime("us", "UTC")))


def _paradas(ruta: Ruta, masa_t: float, pf: Perfil, rng: random.Random) -> list[tuple[float, float, bool]]:
    """Descansos cada ~4,5 h de manejo y una noche si el viaje pasa de 12 h."""
    vm, _, _, dt = perfil(ruta, masa_t, pf.camion, pf.manejo)
    t_km = np.concatenate(([0.0], np.cumsum(dt)))
    total = t_km[-1]
    paradas = []
    if total > DORMIR_SI_MAS_DE_S:
        km = float(np.interp(total * rng.uniform(0.5, 0.6), t_km, ruta.km))
        paradas.append((km, rng.uniform(5, 7) * 3600, pf.ralenti_en_paradas))
    k = 1
    while DESCANSO_CADA_S * k < total - 1800:
        km = float(np.interp(DESCANSO_CADA_S * k + rng.uniform(-1800, 1800), t_km, ruta.km))
        if all(abs(km - p[0]) > 60 for p in paradas):
            paradas.append((km, rng.uniform(20, 40) * 60, pf.ralenti_en_paradas))
        k += 1
    return sorted(paradas)


def _lentos(ruta: Ruta, rng: random.Random) -> list[tuple[float, float, float]]:
    """Salida y entrada a la ciudad con tráfico, y alguna obra en la vía."""
    out = [(0.0, 25.0, rng.uniform(0.5, 0.8)), (ruta.largo_km - 20, ruta.largo_km, rng.uniform(0.6, 0.9))]
    for _ in range(rng.randint(0, 2)):
        km = rng.uniform(40, ruta.largo_km - 40)
        out.append((km, km + rng.uniform(2, 6), rng.uniform(0.35, 0.6)))
    return out


def simular_flota(rutas: dict[str, Ruta], seed: int = SEED, aliases=None):
    """Telemetría por vehículo, viajes y reportes guionados."""
    rng = random.Random(seed)
    pfs = perfiles(rng)
    guiones = {(g.alias, g.viaje_replay): g for g in GUIONES}
    frames, viajes, reportes = {}, [], []
    for corredor, flota in FLOTA.items():
        ida = rutas[corredor]
        _, a, b = CORREDORES[corredor]
        for alias in flota:
            vr = random.Random(f"{seed}-{alias}")
            pf = pfs[alias]
            sentido = "ida" if vr.random() < 0.5 else "vuelta"
            t = INICIO + vr.uniform(0, 30) * 3600
            tramos: list[Tramo] = []
            n_viaje = n_replay = 0
            while t < FIN:
                ruta = ida if sentido == "ida" else ida.invertida()
                origen, destino = (a, b) if sentido == "ida" else (b, a)
                masa = vr.uniform(*CARGA_T[(corredor, sentido)])
                paradas = _paradas(ruta, masa, pf, vr)
                lentos = _lentos(ruta, vr)
                calentamiento = pf.calentamiento_s if not pf.ralenti_en_paradas else vr.uniform(40, 60) * 60
                g = guiones.get((alias, n_replay + 1)) if t + calentamiento >= REPLAY_DESDE else None
                if g and g.tipo == "espera_terminal":
                    calentamiento = g.dur_s
                if g and g.tipo == "carga_completa":
                    masa = CARGA_T[(corredor, sentido)][1] + 2
                if g and g.tipo in ("parada_sin_explicar", "parada_explicada"):
                    km = ruta.largo_km * g.km_frac
                    paradas = sorted([p for p in paradas if abs(p[0] - km) > 60] + [(km, g.dur_s, g.tipo == "parada_explicada" and pf.ralenti_en_paradas)])
                tramos.append(_quieto(t, calentamiento, ruta.lat[0], ruta.lon[0], ruta.alt_m[0], pf.camion))
                salida = t + calentamiento
                pv = pf
                if pf.condicion_replay and salida >= REPLAY_DESDE:
                    pv = replace(pf, camion=replace(pf.camion, condicion=pf.condicion_replay))
                tr, llegada = simular_viaje(ruta, masa, pv, salida, paradas, lentos)
                tramos += tr
                n_viaje += 1
                trip_id = f"{alias}-V{n_viaje:02d}"
                if salida >= REPLAY_DESDE:
                    n_replay += 1
                if g and g.reporte:
                    if g.tipo == "espera_terminal":
                        at = t + g.dur_s * 0.6
                    elif g.tipo == "carga_completa":
                        at = salida + (llegada - salida) * g.km_frac
                    else:
                        at = _hora_en_km(tr, ruta, ruta.largo_km * g.km_frac) + 15 * 60
                    reportes.append({"trip_id": trip_id, "at": int(at), "text": g.reporte})
                viajes.append({
                    "alias": alias, "corridor": corredor, "sentido": sentido, "origin_terminal": origen,
                    "dest_terminal": destino, "t_start": int(salida), "t_end": int(llegada),
                    "origin_lat": float(ruta.lat[0]), "origin_lon": float(ruta.lon[0]),
                    "dest_lat": float(ruta.lat[-1]), "dest_lon": float(ruta.lon[-1]),
                    "trip_id": trip_id, "carga_t": round(masa, 1), "km_ruta": round(ruta.largo_km, 1),
                })
                # llegada: un rato en ralentí y estancia larga con el motor apagado (carga y descarga)
                tramos.append(_quieto(llegada, vr.uniform(8, 15) * 60, ruta.lat[-1], ruta.lon[-1], ruta.alt_m[-1], pf.camion))
                t = llegada + vr.uniform(5, 11) * 3600
                sentido = "vuelta" if sentido == "ida" else "ida"
            if aliases is None or alias in aliases:
                frames[alias] = _frame(alias, tramos, np.random.default_rng(vr.randrange(2**32)),
                                       odo0=vr.uniform(180_000, 620_000), fuel0=vr.uniform(40_000, 160_000))
    viajes = [v for v in viajes if v["t_start"] < FIN and v["t_end"] <= FIN]
    return frames, viajes, reportes, pfs


def _hora_en_km(tramos: list[Tramo], ruta: Ruta, km: float) -> float:
    """Hora en que el viaje pasa por un km (la primera muestra a menos de 300 m)."""
    for tr in tramos:
        d = tp.haversine_km(tr.lat, tr.lon, float(np.interp(km, ruta.km, ruta.lat)), float(np.interp(km, ruta.km, ruta.lon)))
        i = np.flatnonzero(d < 0.3)
        if len(i):
            return float(tr.t[i[0]])
    return float(tramos[0].t[0])


def resumen_viajes(frames: dict[str, pl.DataFrame], viajes: pl.DataFrame) -> pl.DataFrame:
    """km, litros y L/100 km observados de cada viaje (integral del consumo, como las pasadas)."""
    rows = []
    for v in viajes.iter_rows(named=True):
        df = frames.get(v["alias"])
        if df is None:
            continue
        t, lat, lon, fuel = tp._arrays(df)
        lo, hi = np.searchsorted(t, v["t_start"]), np.searchsorted(t, v["t_end"], side="right")
        dt = np.diff(t[lo:hi])
        km = float(tp.haversine_km(lat[lo:hi - 1], lon[lo:hi - 1], lat[lo + 1:hi], lon[lo + 1:hi]).sum())
        litros = float((fuel[lo:hi - 1] * np.minimum(dt, tp.MAX_FUEL_DT_S) / 3600).sum())
        rows.append({"trip_id": v["trip_id"], "km": round(km, 1), "liters": round(litros, 1),
                     "l_per_100km": round(litros / km * 100, 2) if km else None})
    return pl.DataFrame(rows)


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def run(out: Path, fixtures: Path | None = DEFAULT_FIXTURES, seed: int = SEED, demo=DEMO_ALIASES) -> dict:
    t0 = time.time()
    out.mkdir(parents=True, exist_ok=True)
    log("1/5 flota sintética sobre las rutas de Perú (28 vehículos, 19 días)")
    frames, viajes, reportes, _ = simular_flota(cargar(), seed)
    trips_all = pl.DataFrame(viajes).sort(["alias", "t_start"])
    log("2/5 pasadas y línea base offline")
    passes = []
    for v in trips_all.iter_rows(named=True):
        passes += tp.find_passes(frames[v["alias"]], v, v["trip_id"])
    passes_df = pl.DataFrame(passes).with_columns(pl.col("km", "liters", "l_per_100km").round(3))
    base = bl.compute_baseline(passes_df).with_columns(pl.col(pl.Float64).round(3))
    demo_trips = trips_all.filter(pl.col("alias").is_in(list(demo)))
    demo_trips = demo_trips.join(resumen_viajes(frames, demo_trips), on="trip_id", how="left")
    log("3/5 escritura")
    tel = out / "telemetry"
    tel.mkdir(exist_ok=True)
    for alias in demo:
        frames[alias].write_parquet(tel / f"{alias}.parquet")
    demo_trips.write_csv(out / "trips.csv")
    passes_df.filter(pl.col("alias").is_in(list(demo))).with_columns(
        (pl.col("day") <= bl.BASELINE_LAST_DAY).alias("in_baseline")).write_csv(out / "passes_demo.csv")
    base.write_csv(out / "baseline.csv")
    log("4/5 logística sintética (fletes, conductores y reportes)")
    demo_ids = set(demo_trips["trip_id"])
    synth = syn.generate(demo_trips, seed=seed, reportes=[r for r in reportes if r["trip_id"] in demo_ids])
    for name, df in synth.items():
        df.write_csv(out / f"{name}.csv")
    terminales = pl.DataFrame([{"terminal": k, "ciudad": c, "lat": la, "lon": lo} for k, (c, la, lo) in TERMINALES.items()])
    terminales.write_csv(out / "terminals.csv")
    info = {}
    if fixtures is not None:
        log("5/5 fixture")
        info = make_fixture(fixtures, {a: frames[a] for a in demo}, demo_trips, passes_df, base, synth)
    res = {"viajes": len(trips_all), "viajes_demo": len(demo_trips), "pasadas": len(passes_df),
           "tramos_con_linea_base": len(base), "filas_demo": sum(frames[a].height for a in demo), "fixture": info}
    log(f"listo en {time.time() - t0:.0f} s; {res}")
    return res


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("out"))
    ap.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    a = ap.parse_args(argv)
    run(a.out, a.fixtures)


if __name__ == "__main__":
    main()
