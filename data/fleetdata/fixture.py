"""Fixture chico y versionado para los tests del backend (#13).

Ventana corta de telemetría de dos vehículos (CSV, esquema normalizado), más una muestra de la línea
base y de la logística sintética de esos vehículos.
"""
from __future__ import annotations

from pathlib import Path

import polars as pl

from .normalize import to_csv_frame
from .trips import TRAMO_RES

FIXTURE_ALIASES = ("T03", "T07")
WINDOW_S = 30 * 60
WARMUP_S = 10 * 60
MAX_BASELINE_ROWS = 200


def make_fixture(
    out: Path,
    telemetry: dict[str, pl.DataFrame],
    trips: pl.DataFrame,
    passes: pl.DataFrame,
    baseline: pl.DataFrame,
    synthetic: dict[str, pl.DataFrame],
    aliases=FIXTURE_ALIASES,
    window_s: int = WINDOW_S,
) -> dict:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    windows, parts = [], []
    for alias in aliases:
        tr = trips.filter(pl.col("alias") == alias).sort("t_start")
        if tr.is_empty() or alias not in telemetry:
            continue
        start = int(tr["t_start"][0]) + WARMUP_S
        df = telemetry[alias].filter(
            (pl.col("event_time").dt.epoch("s") >= start) & (pl.col("event_time").dt.epoch("s") < start + window_s)
        )
        parts.append(df)
        windows.append((alias, start))
    tel = pl.concat(parts) if parts else pl.DataFrame()
    to_csv_frame(tel).write_csv(out / "telemetry.csv")

    used = {a for a, _ in windows}
    fr = synthetic["freights"].filter(pl.col("alias").is_in(used))
    trip_ids = fr["trip_id"].to_list()
    fr.write_csv(out / "freights.csv")
    trips.filter(pl.col("trip_id").is_in(trip_ids)).write_csv(out / "trips.csv")
    synthetic["drivers"].filter(pl.col("driver_id").is_in(fr["driver_id"].to_list())).write_csv(out / "drivers.csv")
    synthetic["driver_reports"].filter(pl.col("trip_id").is_in(trip_ids)).write_csv(out / "driver_reports.csv")

    # línea base de los tramos que las ventanas tocan y de los tramos de sus viajes
    cells = passes.filter(pl.col("alias").is_in(used))[["corridor", "sentido", "h3_cell"]].unique()
    sample = baseline.join(cells, on=["corridor", "sentido", "h3_cell"], how="inner").head(MAX_BASELINE_ROWS)
    sample.write_csv(out / "baseline_sample.csv")
    return {"rows": len(tel), "windows": windows, "baseline_rows": len(sample), "freights": len(fr), "tramo_res": TRAMO_RES}
