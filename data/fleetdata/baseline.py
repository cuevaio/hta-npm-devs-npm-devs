"""Línea base offline por tramo (celda H3 res. 6 + sentido) con la flota completa (ADR 0009).

Solo se calcula con pasadas de los días 1-12; un tramo con menos de 3 pasadas no tiene línea base
y no aparece en la salida. Nunca es por vehículo: solo salen agregados.
"""
from __future__ import annotations

import polars as pl

BASELINE_LAST_DAY = 12
MIN_PASSES = 3

BASELINE_COLUMNS = (
    "corridor", "sentido", "h3_cell", "n_passes", "n_vehicles",
    "median_l_per_100km", "p90_l_per_100km", "median_liters", "p90_liters", "median_km",
    "provenance",
)


def compute_baseline(
    passes: pl.DataFrame, last_day: int = BASELINE_LAST_DAY, min_passes: int = MIN_PASSES
) -> pl.DataFrame:
    if passes.is_empty():
        return pl.DataFrame(schema={c: pl.String for c in BASELINE_COLUMNS})
    return (
        passes.filter(pl.col("day") <= last_day)
        .group_by(["corridor", "sentido", "h3_cell"])
        .agg(
            pl.len().alias("n_passes"),
            pl.col("alias").n_unique().alias("n_vehicles"),
            pl.col("l_per_100km").median().alias("median_l_per_100km"),
            pl.col("l_per_100km").quantile(0.9, "linear").alias("p90_l_per_100km"),
            pl.col("liters").median().alias("median_liters"),
            pl.col("liters").quantile(0.9, "linear").alias("p90_liters"),
            pl.col("km").median().alias("median_km"),
        )
        .filter(pl.col("n_passes") >= min_passes)
        .with_columns(pl.lit("model_inferred").alias("provenance"))
        .select(BASELINE_COLUMNS)
        .sort(["corridor", "sentido", "h3_cell"])
    )
