"""Pipeline de punta a punta.

    uv run python -m fleetdata.pipeline --archive ems-dataset-2.tar.gz --alias-map alias.json --out data/out
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import polars as pl

from . import baseline as bl
from . import synthetic as syn
from . import trips as tp
from .anonymize import anonymize
from .download import ensure_archive
from .extract import DEMO_ALIASES, FLEET_ALIASES, iter_rows, load_alias_map, select_hashes
from .fixture import FIXTURE_ALIASES, make_fixture
from .normalize import Telemetry, normalize_row, to_csv_frame
from .pii import scan_dir

DEFAULT_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def collect(archive: Path, alias_map: dict[str, str], aliases) -> dict[str, pl.DataFrame]:
    """Extrae, anonimiza y normaliza en un solo recorrido del tar (los datos personales no se guardan)."""
    hashes = select_hashes(alias_map, aliases)
    buffers: dict[str, Telemetry] = {}
    n = 0
    for row in anonymize(iter_rows(archive, hashes), hashes):
        buffers.setdefault(row["alias"], Telemetry()).append(normalize_row(row))
        n += 1
        if n % 2_000_000 == 0:
            log(f"  {n:,} filas ({row['ems_time']})")
    log(f"  {n:,} filas en total")
    return {a: b.to_frame(a) for a, b in sorted(buffers.items())}


def analyze(frames: dict[str, pl.DataFrame], demo_aliases) -> dict:
    stays = []
    for alias, df in frames.items():
        stays += tp.find_stays(alias, df)
    terminals = tp.find_terminals(stays)
    trips, passes = [], []
    for alias, df in frames.items():
        mine = tp.build_trips(alias, [s for s in stays if s.alias == alias], terminals)
        for n, trip in enumerate(sorted(mine, key=lambda t: t["t_start"]), 1):
            trip["trip_id"] = f"{alias}-V{n:02d}"
            passes += tp.find_passes(df, trip, trip["trip_id"])
            trips.append(trip)
    trips_df = pl.DataFrame(trips) if trips else pl.DataFrame()
    passes_df = pl.DataFrame(passes) if passes else pl.DataFrame()
    if not passes_df.is_empty():
        passes_df = passes_df.with_columns(pl.col("km", "liters", "l_per_100km").round(3))
    base = bl.compute_baseline(passes_df)
    base = base.with_columns(pl.col(pl.Float64).round(3))
    return {"terminals": terminals, "trips": trips_df, "passes": passes_df, "baseline": base}


def run(archive: Path, alias_map_path: Path, out: Path, fixtures: Path, demo=DEMO_ALIASES, verify=True, fixture_aliases=FIXTURE_ALIASES) -> None:
    t0 = time.time()
    out.mkdir(parents=True, exist_ok=True)
    log("1/6 archivo y checksum")
    if verify:
        ensure_archive(archive)
    alias_map = load_alias_map(alias_map_path)
    log("2/6 extracción, anonimización y normalización (28 vehículos, streaming)")
    frames = collect(archive, alias_map, FLEET_ALIASES)
    tel_dir = out / "telemetry"
    tel_dir.mkdir(exist_ok=True)
    for alias in demo:
        if alias in frames:
            frames[alias].write_parquet(tel_dir / f"{alias}.parquet")
    log("3/6 viajes, pasadas y línea base offline")
    res = analyze(frames, demo)
    demo_trips = res["trips"].filter(pl.col("alias").is_in(list(demo)))
    demo_trips.write_csv(out / "trips.csv")
    res["passes"].filter(pl.col("alias").is_in(list(demo))).with_columns(
        (pl.col("day") <= bl.BASELINE_LAST_DAY).alias("in_baseline")
    ).write_csv(out / "passes_demo.csv")
    res["baseline"].write_csv(out / "baseline.csv")
    log("4/6 logística sintética")
    synth = syn.generate(demo_trips)
    for name, df in synth.items():
        df.write_csv(out / f"{name}.csv")
    log("5/6 fixture")
    info = make_fixture(fixtures, {a: frames[a] for a in demo if a in frames}, demo_trips, res["passes"], res["baseline"], synth, aliases=fixture_aliases)
    log("6/6 verificación de datos personales")
    hits = scan_dir(out, alias_map.keys()) + scan_dir(fixtures, alias_map.keys())
    if hits:
        raise SystemExit(f"Datos personales en la salida: {hits[:5]}")
    log(f"listo en {time.time() - t0:.0f} s; terminales={len(set(res['terminals'].values()))} viajes={len(res['trips'])} "
        f"tramos con línea base={len(res['baseline'])} fixture={info}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive", type=Path, required=True, help="tar.gz de EMS dataset-2 (se descarga si no existe)")
    ap.add_argument("--alias-map", type=Path, required=True, help="JSON privado hash -> alias (fuera del repo)")
    ap.add_argument("--out", type=Path, default=Path("out"))
    ap.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    a = ap.parse_args(argv)
    run(a.archive, a.alias_map, a.out, a.fixtures)


if __name__ == "__main__":
    main()
