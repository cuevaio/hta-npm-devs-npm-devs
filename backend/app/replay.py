"""Motor del replay (ADR 0005): estado único en Postgres, reloj inyectable.

`tick(now)` avanza la hora del replay según el tiempo real transcurrido por la velocidad y copia
de `telemetry_source` a `telemetry_reading` las lecturas con hora del evento en (anterior, nueva].
Cada lectura conserva sus tres horas: del evento, de replay e de ingesta.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Callable

import psycopg
from psycopg.rows import dict_row

from .schemas import ReplayState

Clock = Callable[[], datetime]

_COLUMNS = "alias, event_time, lat, lon, speed_kmh, rpm, fuel_rate_lph, fuel_total_l, odometer_km, engine_on, provenance"


def system_clock() -> datetime:
    return datetime.now(UTC)


class ReplayEngine:
    def __init__(self, database_url: str, clock: Clock = system_clock):
        self.database_url = database_url
        self.clock = clock

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def state(self) -> tuple[ReplayState, datetime]:
        """Estado actual y hora de última actualización."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM replay_state").fetchone()
        return _model(row), row["updated_at"]

    # --- avance ---

    def tick(self, now: datetime | None = None) -> None:
        now = now or self.clock()
        with self._connect() as conn:
            self._tick(conn, now)

    def _tick(self, conn: psycopg.Connection, now: datetime) -> dict:
        row = conn.execute("SELECT * FROM replay_state FOR UPDATE").fetchone()
        if row["estado"] == "playing":
            elapsed = max(now - row["last_tick_at"], timedelta(0))
            new = min(row["hora_replay"] + elapsed * row["velocidad"], row["fin"])
            if new > row["hora_replay"]:
                self._copy_range(conn, row["hora_replay"], new, now)
            estado = "paused" if new >= row["fin"] else "playing"
            conn.execute(
                "UPDATE replay_state SET hora_replay = %s, estado = %s, last_tick_at = %s,"
                " updated_at = CASE WHEN %s THEN %s ELSE updated_at END",
                (new, estado, now, new > row["hora_replay"] or estado != "playing", now),
            )
        else:
            conn.execute("UPDATE replay_state SET last_tick_at = %s", (now,))
        return conn.execute("SELECT * FROM replay_state").fetchone()

    @staticmethod
    def _copy_range(conn: psycopg.Connection, lo: datetime, hi: datetime, now: datetime) -> None:
        conn.execute(
            f"INSERT INTO telemetry_reading ({_COLUMNS}, replayed_at, ingested_at) "
            f"SELECT {_COLUMNS}, %s, %s FROM telemetry_source "
            "WHERE event_time > %s AND event_time <= %s ORDER BY event_time",
            (hi, now, lo, hi),
        )

    # --- control (control_replay) ---

    def _update(self, sql: str, params: tuple, now: datetime | None = None) -> None:
        now = now or self.clock()
        with self._connect() as conn:
            self._tick(conn, now)  # cierra el tramo anterior con la velocidad y estado anteriores
            conn.execute(f"UPDATE replay_state SET {sql}, updated_at = %s", (*params, now))

    def play(self) -> None:
        self._update("estado = 'playing'", ())

    def pause(self) -> None:
        self._update("estado = 'paused'", ())

    def set_speed(self, speed: float) -> None:
        self._update("velocidad = %s", (speed,))

    def seek(self, to: datetime) -> None:
        """Salta a `to`. Hacia atrás borra lo reproducido después; hacia adelante reproduce lo intermedio."""
        now = self.clock()
        with self._connect() as conn:
            row = self._tick(conn, now)
            if to < row["hora_replay"]:
                conn.execute("DELETE FROM telemetry_reading WHERE replayed_at IS NOT NULL AND event_time > %s", (to,))
            elif to > row["hora_replay"]:
                self._copy_range(conn, row["hora_replay"], to, now)
            conn.execute("UPDATE replay_state SET hora_replay = %s, updated_at = %s", (to, now))

    # --- tarea asyncio ---

    async def run(self, interval: float = 1.0) -> None:
        while True:
            await asyncio.sleep(interval)
            try:
                await asyncio.to_thread(self.tick)
            except psycopg.Error:
                pass  # la base puede no estar disponible un instante; el próximo tick reintenta


def _model(row: dict) -> ReplayState:
    return ReplayState(
        estado=row["estado"], velocidad=row["velocidad"], hora_replay=row["hora_replay"],
        inicio=row["inicio"], fin=row["fin"],
    )
