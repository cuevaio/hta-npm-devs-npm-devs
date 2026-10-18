"""Carga la salida del pipeline de data/ en Cloud SQL (D33). Nunca copia datos al repositorio.

Uso: uv run --group dev python scripts/load_demo_data.py --source <out/> --database-url <url>

Días 1-12 (hora del evento hasta el 2020-04-13 00:00 UTC+8) van a `telemetry_reading` como historia
(`replayed_at` nulo); los días 13-19 van a `telemetry_source`, que reproduce el replay. Es
idempotente: recarga todo desde cero y deja el replay en pausa al inicio.
"""

import argparse
import io
import sys
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import migrate  # noqa: E402

REPLAY_START = datetime(2020, 4, 12, 16, 0, tzinfo=UTC)  # 2020-04-13 00:00 UTC+8
TELEMETRY = ["alias", "event_time", "lat", "lon", "speed_kmh", "rpm", "fuel_rate_lph", "fuel_total_l",
             "odometer_km", "engine_on", "provenance"]
TRIPS = ["trip_id", "alias", "corridor", "sentido", "origin_terminal", "dest_terminal", "t_start", "t_end"]
FREIGHTS = ["trip_id", "freight_id", "alias", "driver_id", "client", "cargo", "corridor", "sentido",
            "origin_terminal", "dest_terminal", "planned_departure", "provenance"]
DRIVERS = ["driver_id", "name", "provenance"]
PASSES = ["trip_id", "alias", "corridor", "sentido", "h3_cell", "t_start", "t_end", "day", "km", "liters",
          "l_per_100km", "in_baseline"]
BASELINES = ["corridor", "sentido", "h3_cell", "n_passes", "n_vehicles", "median_l_per_100km", "p90_l_per_100km",
             "median_liters", "p90_liters", "median_km", "provenance"]
REPORTS = ["report_id", "trip_id", "driver_id", "reported_at", "text", "provenance"]


def _utc(df: pl.DataFrame, *columns: str) -> pl.DataFrame:
    """Normaliza columnas de tiempo (ISO o epoch en segundos) a datetime UTC."""
    for c in columns:
        dtype = df.schema[c]
        if dtype.is_integer():
            df = df.with_columns(pl.from_epoch(c, "s").dt.replace_time_zone("UTC"))
        elif dtype == pl.String:
            df = df.with_columns(pl.col(c).str.to_datetime(time_zone="UTC", time_unit="us"))
        elif getattr(dtype, "time_zone", None) is None:
            df = df.with_columns(pl.col(c).dt.replace_time_zone("UTC"))
    return df


def _copy(conn: psycopg.Connection, table: str, df: pl.DataFrame, columns: list[str]) -> int:
    if df.is_empty():
        return 0
    buf = io.BytesIO()
    df.select(columns).write_csv(buf, datetime_format="%Y-%m-%dT%H:%M:%S%.6fZ")
    with conn.cursor().copy(f"COPY {table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT csv, HEADER true)") as cp:
        cp.write(buf.getvalue())
    return df.height


def _telemetry_files(source: Path) -> list[Path]:
    files = sorted((source / "telemetry").glob("*.parquet"))
    if files:
        return files
    csv = source / "telemetry.csv"
    if csv.exists():
        return [csv]
    raise SystemExit(f"{source}: no hay telemetry/*.parquet ni telemetry.csv")


def _read_telemetry(path: Path) -> pl.DataFrame:
    df = pl.read_parquet(path) if path.suffix == ".parquet" else pl.read_csv(path)
    return _utc(df, "event_time")


def load(source: Path, database_url: str, replay_start: datetime = REPLAY_START) -> dict[str, int]:
    migrate(database_url)
    counts = {"history": 0, "source": 0}
    last_event = replay_start
    with psycopg.connect(database_url) as conn:
        conn.execute("TRUNCATE baselines, passes, telemetry_reading, telemetry_source, driver_reports, freights, trips, drivers, vehicles")
        aliases: set[str] = set()
        for path in _telemetry_files(source):
            df = _read_telemetry(path)
            aliases |= set(df["alias"].unique())
            history = df.filter(pl.col("event_time") <= replay_start)
            future = df.filter(pl.col("event_time") > replay_start)
            if not future.is_empty():
                last_event = max(last_event, future["event_time"].max())
            counts["history"] += _copy(conn, "telemetry_reading", history, TELEMETRY)
            counts["source"] += _copy(conn, "telemetry_source", future, TELEMETRY)
        trips = _utc(pl.read_csv(source / "trips.csv"), "t_start", "t_end")
        aliases |= set(trips["alias"].unique())
        conn.execute("INSERT INTO vehicles (alias) SELECT unnest(%s::text[]) ON CONFLICT DO NOTHING", (sorted(aliases),))
        _copy(conn, "drivers", pl.read_csv(source / "drivers.csv"), DRIVERS)
        _copy(conn, "trips", trips, TRIPS)
        _copy(conn, "freights", _utc(pl.read_csv(source / "freights.csv"), "planned_departure"), FREIGHTS)
        _copy(conn, "passes", _utc(pl.read_csv(source / "passes_demo.csv"), "t_start", "t_end"), PASSES)
        _copy(conn, "baselines", pl.read_csv(source / "baseline.csv"), BASELINES)
        _copy(conn, "driver_reports", _utc(pl.read_csv(source / "driver_reports.csv"), "reported_at"), REPORTS)
        conn.execute(
            "UPDATE replay_state SET estado = 'paused', velocidad = 1, hora_replay = %s, inicio = %s, fin = %s,"
            " last_tick_at = now(), updated_at = now()",
            (replay_start, replay_start, last_event),
        )
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, required=True, help="salida del pipeline de data/")
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--replay-start", type=datetime.fromisoformat, default=REPLAY_START,
                        help="fin de la historia (por defecto 2020-04-12T16:00:00+00:00)")
    args = parser.parse_args()
    counts = load(args.source, args.database_url, args.replay_start)
    print(f"historia: {counts['history']:,} lecturas; por reproducir: {counts['source']:,}")


if __name__ == "__main__":
    main()
