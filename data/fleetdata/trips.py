"""Viajes y pasadas a partir de la telemetría normalizada.

- Estancia larga: vehículo prácticamente quieto durante >= 3 h (ADR 0009 / D33). Con el motor apagado
  no hay filas, así que un hueco largo sin movimiento cuenta como estancia.
- Terminal: grupo de celdas H3 (res. 5) donde varias estancias largas de la flota coinciden.
- Viaje: recorrido entre dos estancias largas consecutivas en terminales distintos. El corredor es el par
  de terminales y el sentido sale del terminal de origen (ida = el de menor id).
- Pasada: recorrido de una celda H3 res. 6 dentro de un viaje (ADR 0008), con su consumo observado:
  integral de x7001 (L/h) y distancia GPS, nunca x7002 ni el odómetro.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl
from h3.api.basic_int import grid_disk, latlng_to_cell

LONG_STAY_S = 3 * 3600
STAY_MAX_KMH = 3.0
TERMINAL_RES = 5
TRAMO_RES = 6
MIN_STAYS_PER_TERMINAL = 3
MAX_FUEL_DT_S = 10  # un hueco de GPS no se integra como consumo
MIN_PASS_KM = 2.0
MIN_PASS_COVERAGE = 0.8
BASE_DAY0_UTC = "2020-04-01"
UTC_OFFSET_S = 8 * 3600  # los días de la flota se cuentan en hora local (ver normalize)


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0088 * np.arcsin(np.sqrt(a))


@dataclass(frozen=True)
class Stay:
    alias: str
    t0: int
    t1: int
    lat: float
    lon: float


def _arrays(df: pl.DataFrame):
    d = df.drop_nulls(["event_time"]).sort("event_time")
    t = d["event_time"].dt.epoch("s").to_numpy().astype(np.int64)
    lat = d["lat"].fill_null(strategy="forward").fill_null(strategy="backward").to_numpy()
    lon = d["lon"].fill_null(strategy="forward").fill_null(strategy="backward").to_numpy()
    fuel = d["fuel_rate_lph"].fill_null(0.0).to_numpy()
    return t, lat, lon, fuel


def find_stays(alias: str, df: pl.DataFrame, min_s: int = LONG_STAY_S) -> list[Stay]:
    t, lat, lon, _ = _arrays(df)
    if len(t) < 2:
        return []
    dist = haversine_km(lat[:-1], lon[:-1], lat[1:], lon[1:])
    dt_h = np.maximum(np.diff(t), 1) / 3600
    still = (dist / dt_h) < STAY_MAX_KMH  # pares (i, i+1) en reposo
    stays: list[Stay] = []
    i = 0
    n = len(still)
    while i < n:
        if not still[i]:
            i += 1
            continue
        j = i
        while j < n and still[j]:
            j += 1
        # filas i..j (inclusive) forman una estancia
        if t[j] - t[i] >= min_s:
            stays.append(Stay(alias, int(t[i]), int(t[j]), float(np.median(lat[i : j + 1])), float(np.median(lon[i : j + 1]))))
        i = j
    return stays


def find_terminals(stays: list[Stay], min_stays: int = MIN_STAYS_PER_TERMINAL) -> dict[int, str]:
    """Celda H3 res. 5 -> id de terminal (K01…), agrupando celdas contiguas."""
    count: dict[int, int] = {}
    for s in stays:
        c = latlng_to_cell(s.lat, s.lon, TERMINAL_RES)
        count[c] = count.get(c, 0) + 1
    # una celda candidata arrastra a sus vecinas con estancias
    cells = set(count)
    parent = {c: c for c in cells}

    def root(c):
        while parent[c] != c:
            parent[c] = parent[parent[c]]
            c = parent[c]
        return c

    for c in cells:
        for nb in grid_disk(c, 1):
            if nb in cells:
                parent[root(nb)] = root(c)
    groups: dict[int, list[int]] = {}
    for c in cells:
        groups.setdefault(root(c), []).append(c)
    kept = [sorted(g) for g in groups.values() if sum(count[c] for c in g) >= min_stays]
    kept.sort(key=lambda g: g[0])
    out: dict[int, str] = {}
    for k, g in enumerate(kept, 1):
        for c in g:
            out[c] = f"K{k:02d}"
    return out


def terminal_of(stay: Stay, terminals: dict[int, str]) -> str | None:
    return terminals.get(latlng_to_cell(stay.lat, stay.lon, TERMINAL_RES))


def build_trips(alias: str, stays: list[Stay], terminals: dict[int, str]) -> list[dict]:
    at_terminal = [(s, terminal_of(s, terminals)) for s in sorted(stays, key=lambda s: s.t0)]
    at_terminal = [(s, k) for s, k in at_terminal if k]
    trips = []
    for (a, ka), (b, kb) in zip(at_terminal, at_terminal[1:]):
        if ka == kb:
            continue
        first, second = sorted((ka, kb))
        trips.append(
            {
                "alias": alias,
                "corridor": f"{first}-{second}",
                "sentido": "ida" if ka == first else "vuelta",
                "origin_terminal": ka,
                "dest_terminal": kb,
                "t_start": a.t1,
                "t_end": b.t0,
                "origin_lat": a.lat,
                "origin_lon": a.lon,
                "dest_lat": b.lat,
                "dest_lon": b.lon,
            }
        )
    return trips


def day_of(epoch_s: int, day0_utc: str = BASE_DAY0_UTC) -> int:
    """Día 1…N de la flota (hora local UTC+8; el día 1 es el 2020-04-01)."""
    from datetime import datetime, timezone

    base = int(datetime.fromisoformat(day0_utc).replace(tzinfo=timezone.utc).timestamp())
    return (epoch_s + UTC_OFFSET_S - base) // 86400 + 1


def find_passes(df: pl.DataFrame, trip: dict, trip_id: str) -> list[dict]:
    """Pasadas de celdas H3 res. 6 dentro de un viaje (sin la primera ni la última celda, que son parciales)."""
    t, lat, lon, fuel = _arrays(df)
    lo, hi = np.searchsorted(t, trip["t_start"]), np.searchsorted(t, trip["t_end"], side="right")
    t, lat, lon, fuel = t[lo:hi], lat[lo:hi], lon[lo:hi], fuel[lo:hi]
    if len(t) < 3:
        return []
    cells = np.fromiter((latlng_to_cell(a, b, TRAMO_RES) for a, b in zip(lat, lon)), dtype=np.uint64, count=len(t))
    dt = np.diff(t)
    step_km = haversine_km(lat[:-1], lon[:-1], lat[1:], lon[1:])
    step_l = fuel[:-1] * np.minimum(dt, MAX_FUEL_DT_S) / 3600
    step_ok = dt <= MAX_FUEL_DT_S
    # fronteras de corrida: filas donde cambia la celda
    change = np.flatnonzero(cells[1:] != cells[:-1]) + 1
    bounds = np.concatenate(([0], change, [len(t)]))
    runs = list(zip(bounds[:-1], bounds[1:]))
    passes = []
    for a, b in runs[1:-1]:  # fuera la primera y la última
        # los pasos a..b-1 van de la fila i a la i+1 dentro de la corrida
        sl = slice(a, b - 1)
        km = float(step_km[sl].sum())
        dur = int(t[b - 1] - t[a])
        if km < MIN_PASS_KM or dur <= 0:
            continue
        if step_ok[sl].sum() < MIN_PASS_COVERAGE * (b - 1 - a):
            continue
        liters = float(step_l[sl].sum())
        passes.append(
            {
                "trip_id": trip_id,
                "alias": trip["alias"],
                "corridor": trip["corridor"],
                "sentido": trip["sentido"],
                "h3_cell": format(int(cells[a]), "x"),
                "t_start": int(t[a]),
                "t_end": int(t[b - 1]),
                "day": int(day_of(int(t[a]))),
                "km": km,
                "liters": liters,
                "l_per_100km": liters / km * 100,
            }
        )
    return passes
