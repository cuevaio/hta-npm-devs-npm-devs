"""Viajes y análisis de combustible desde Postgres: pasadas visibles frente a la línea base de su tramo y sentido."""

from datetime import datetime

import psycopg

from .db import connect
from .schemas import FuelAnalysis, LineaBase, Pasada, Flete, Tramo, TripStatus

MIN_PASSES = 3  # ADR 0009
MIN_VEHICLES = 2  # pares = otros vehículos en el mismo tramo y sentido (ADR 0002)
OVER_FACTOR = 1.25  # D33
IDLE_SPEED_KMH = 0.5
IDLE_GAP_CAP_S = 10  # un hueco de telemetría no cuenta entero como ralentí

_TRIP = """
SELECT t.trip_id, t.alias, t.corridor, t.sentido, t.origin_terminal, t.dest_terminal, t.t_start, t.t_end,
       f.freight_id, f.client, f.cargo, d.name AS driver
FROM trips t
LEFT JOIN freights f ON f.trip_id = t.trip_id
LEFT JOIN drivers d ON d.driver_id = f.driver_id
WHERE t.trip_id = %s
"""

_PASSES = """
SELECT p.h3_cell, p.sentido, p.t_start, p.t_end, p.km, p.liters,
       b.n_passes, b.n_vehicles, b.median_l_per_100km, b.p90_l_per_100km, b.median_liters, b.p90_liters,
       p.l_per_100km,
       COALESCE((
           SELECT sum(least(extract(epoch FROM r.nxt - r.event_time), %(cap)s)) FROM (
               SELECT event_time, speed_kmh, rpm, lead(event_time) OVER (ORDER BY event_time) AS nxt
               FROM telemetry_reading
               WHERE alias = p.alias AND event_time >= p.t_start AND event_time < p.t_end
           ) r
           WHERE r.nxt IS NOT NULL AND r.speed_kmh <= %(idle)s AND r.rpm > 0
       ), 0) / 60.0 AS ralenti_min
FROM passes p
LEFT JOIN baselines b ON b.corridor = p.corridor AND b.sentido = p.sentido AND b.h3_cell = p.h3_cell
WHERE p.trip_id = %(trip)s AND p.t_end <= %(hora)s
ORDER BY p.t_start
"""


def _hora(conn: psycopg.Connection) -> tuple[datetime, datetime]:
    st = conn.execute("SELECT hora_replay, updated_at FROM replay_state").fetchone()
    return st["hora_replay"], st["updated_at"]


def evaluar(row: dict) -> tuple[bool, bool]:
    """(línea base válida, sobreconsumo) de una pasada con las columnas de su línea base."""
    valid = (row["n_passes"] or 0) >= MIN_PASSES and (row["n_vehicles"] or 0) >= MIN_VEHICLES
    rate = row["l_per_100km"]
    over = bool(
        valid and rate is not None
        and rate >= OVER_FACTOR * row["median_l_per_100km"] and rate > row["p90_l_per_100km"]
    )
    return valid, over


def _pasada(row: dict) -> Pasada:
    valid, over = evaluar(row)
    base = LineaBase(mediana_l=row["median_liters"], p90_l=row["p90_liters"], n_pasadas=row["n_passes"]) if valid else None
    return Pasada(
        tramo=Tramo(h3=row["h3_cell"], sentido=row["sentido"]), consumo_observado_l=row["liters"],
        linea_base=base, sobreconsumo=over, exceso_l=round(row["liters"] - row["median_liters"], 3) if valid else None,
        ralenti_min=round(row["ralenti_min"], 2),
    )


def fuel_analysis(database_url: str, trip_id: str) -> tuple[FuelAnalysis, datetime, datetime, datetime] | None:
    """Devuelve (datos, desde, hasta, actualizado_en), o None si el viaje es desconocido."""
    with connect(database_url, dict_rows=True) as conn:
        trip = conn.execute(_TRIP, (trip_id,)).fetchone()
        if trip is None:
            return None
        hora, updated = _hora(conn)
        rows = conn.execute(
            _PASSES, {"trip": trip_id, "hora": hora, "cap": IDLE_GAP_CAP_S, "idle": IDLE_SPEED_KMH}
        ).fetchall()
    pasadas = [_pasada(r) for r in rows]
    km = sum(r["km"] for r in rows)
    liters = sum(p.consumo_observado_l for p in pasadas)
    data = FuelAnalysis(
        viaje_id=trip_id, distancia_km=round(km, 3), consumo_observado_l=round(liters, 3),
        consumo_l_100km=round(liters / km * 100, 2) if km else 0.0,
        exceso_total_l=round(sum(p.exceso_l for p in pasadas if p.exceso_l is not None), 3),
        pasadas=pasadas, anomalias=[],  # las anomalías son #15
    )
    return data, trip["t_start"], max(trip["t_start"], min(hora, trip["t_end"])), updated


def trip_status(database_url: str, trip_id: str) -> tuple[TripStatus, datetime, datetime, datetime] | None:
    """None si el viaje es desconocido. Estado según la hora de replay."""
    with connect(database_url, dict_rows=True) as conn:
        trip = conn.execute(_TRIP, (trip_id,)).fetchone()
        if trip is None:
            return None
        hora, updated = _hora(conn)
        km = conn.execute(
            "SELECT COALESCE(sum(km), 0) AS km FROM passes WHERE trip_id = %s AND t_end <= %s", (trip_id, hora)
        ).fetchone()["km"]
    span = (trip["t_end"] - trip["t_start"]).total_seconds()
    done = hora >= trip["t_end"]
    progreso = 100.0 if done else max(0.0, min(100.0, (hora - trip["t_start"]).total_seconds() / span * 100))
    data = TripStatus(
        viaje_id=trip_id, vehiculo_alias=trip["alias"], conductor=trip["driver"] or "Sin asignar",
        flete=Flete(
            id=trip["freight_id"] or "", carga=trip["cargo"] or "", cliente=trip["client"] or "",
            origen=trip["origin_terminal"], destino=trip["dest_terminal"],
        ),
        corredor=trip["corridor"], sentido=trip["sentido"], estado="finalizado" if done else "en_curso",
        inicio=trip["t_start"], fin=trip["t_end"] if done else None, distancia_km=round(km, 3),
        progreso_pct=round(progreso, 1),
    )
    return data, trip["t_start"], max(trip["t_start"], min(hora, trip["t_end"])), updated
