"""Lecturas de vehículo y flota desde Postgres: última lectura visible por vehículo (DISTINCT ON)."""

from datetime import datetime

import psycopg
from psycopg.rows import dict_row

from .schemas import FleetOverview, Posicion, VehicleStatus, VehiculoResumen

_LAST_READINGS = """
SELECT l.*, t.trip_id, t.corridor, t.sentido, d.name AS conductor
FROM (
    SELECT DISTINCT ON (r.alias) r.alias, r.event_time, r.lat, r.lon, r.speed_kmh, r.rpm
    FROM telemetry_reading r
    WHERE r.event_time <= %(hora)s AND (%(alias)s::text IS NULL OR r.alias = %(alias)s)
    ORDER BY r.alias, r.event_time DESC
) l
LEFT JOIN LATERAL (
    SELECT * FROM trips t
    WHERE t.alias = l.alias AND %(hora)s BETWEEN t.t_start AND t.t_end
    ORDER BY t.t_start DESC LIMIT 1
) t ON true
LEFT JOIN freights f ON f.trip_id = t.trip_id
LEFT JOIN drivers d ON d.driver_id = f.driver_id
ORDER BY l.alias
"""

IN_MOTION_KMH = 3.0
STOPPED_KMH = 0.5


def _estado(row: dict) -> str:
    speed = row["speed_kmh"] or 0.0
    if speed > IN_MOTION_KMH and row["trip_id"]:
        return "en_viaje"
    if speed <= STOPPED_KMH and (row["rpm"] or 0) > 0:
        return "ralenti"
    return "detenido"


def _resumen(row: dict) -> dict:
    return dict(
        alias=row["alias"], estado=_estado(row), viaje_id=row["trip_id"], velocidad_kmh=row["speed_kmh"] or 0.0,
        posicion=Posicion(lat=row["lat"], lon=row["lon"]), hora_evento=row["event_time"],
    )


def _rows(conn: psycopg.Connection, hora: datetime, alias: str | None) -> list[dict]:
    return conn.execute(_LAST_READINGS, {"hora": hora, "alias": alias}).fetchall()


def fleet_overview(database_url: str) -> tuple[FleetOverview, datetime, datetime, datetime]:
    """Devuelve (datos, desde, hasta, actualizado_en); desde/hasta en hora del evento."""
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        st = conn.execute("SELECT * FROM replay_state").fetchone()
        rows = _rows(conn, st["hora_replay"], None)
        total = conn.execute("SELECT count(*) AS n FROM vehicles").fetchone()["n"]
    vehiculos = [VehiculoResumen(**_resumen(r)) for r in rows]
    data = FleetOverview(
        total_vehiculos=total, viajes_en_curso=sum(1 for r in rows if r["trip_id"]),
        alertas_abiertas=0, vehiculos=vehiculos,  # hasta #15
    )
    desde = min([st["inicio"], *(r["event_time"] for r in rows)])
    return data, desde, st["hora_replay"], st["updated_at"]


def vehicle_status(database_url: str, alias: str) -> tuple[VehicleStatus, datetime, datetime, datetime] | None:
    """None si el alias es desconocido o aún no tiene lecturas visibles."""
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        st = conn.execute("SELECT * FROM replay_state").fetchone()
        rows = _rows(conn, st["hora_replay"], alias)
    if not rows:
        return None
    row = rows[0]
    data = VehicleStatus(**_resumen(row), corredor=row["corridor"], sentido=row["sentido"], conductor=row["conductor"])
    return data, min(st["inicio"], row["event_time"]), row["event_time"], st["updated_at"]
