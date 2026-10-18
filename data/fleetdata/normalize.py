"""Normalización de lecturas: hora del evento en UTC, unidades corregidas y procedencia.

Correcciones de unidades (docs/research/fead-ems-dataset2-perfil.md §2.2): el diccionario y el
paper de FEAD etiquetan mal varias señales.

    x7000 -> rpm (el diccionario dice "km/h")
    x7001 -> fuel_rate_lph, L/h (consumo instantáneo)
    x7002 -> fuel_total_l, litros acumulados (el diccionario dice "0,5 L"; es litros con resolución de 0,5)
    x7004 -> speed_kmh (el diccionario dice "0,1 km"; es la velocidad EMS en km/h, corr. 0,989 con el GPS)
    x7005 -> odometer_km, km (el paper dice millas)

`ems_time` no trae zona horaria y es hora local de China (UTC+8): se guarda en UTC (D33).
"""
from __future__ import annotations

import math
from array import array
from datetime import datetime, timedelta, timezone

import polars as pl

PROVENANCE = "fead_observed"
SOURCE_UTC_OFFSET = timedelta(hours=8)
NAN = math.nan
_EPOCH = datetime(1970, 1, 1)

NORMALIZED_COLUMNS = (
    "alias",
    "event_time",
    "lat",
    "lon",
    "speed_kmh",
    "rpm",
    "fuel_rate_lph",
    "fuel_total_l",
    "odometer_km",
    "engine_on",
    "provenance",
)


def _num(v) -> float:
    if v is None or v in ("", "NULL", "\\N"):
        return NAN
    try:
        return float(v)
    except (TypeError, ValueError):
        return NAN


def event_epoch_utc(ems_time: str) -> int:
    local = datetime.strptime(ems_time, "%Y-%m-%d %H:%M:%S")
    return int((local - SOURCE_UTC_OFFSET - _EPOCH).total_seconds())


def normalize_row(row: dict) -> tuple:
    """Fila anónima -> (epoch_utc, lat, lon, speed_kmh, rpm, fuel_rate_lph, fuel_total_l, odometer_km, engine_on)."""
    s = row["signals"]
    rpm = _num(s.get("x7000"))
    return (
        event_epoch_utc(row["ems_time"]),
        _num(row["lat"]),
        _num(row["lon"]),
        _num(s.get("x7004")),
        rpm,
        _num(s.get("x7001")),
        _num(s.get("x7002")),
        _num(s.get("x7005")),
        bool(rpm > 0) if rpm == rpm else False,
    )


class Telemetry:
    """Búfer columnar compacto de un vehículo (decenas de millones de filas entre los 28)."""

    def __init__(self) -> None:
        self.epoch = array("q")
        self.cols = {k: array("d") for k in ("lat", "lon", "speed_kmh", "rpm", "fuel_rate_lph", "fuel_total_l", "odometer_km")}
        self.engine_on = array("b")

    def append(self, t: tuple) -> None:
        self.epoch.append(t[0])
        for key, v in zip(self.cols, t[1:8]):
            self.cols[key].append(v)
        self.engine_on.append(1 if t[8] else 0)

    def __len__(self) -> int:
        return len(self.epoch)

    def to_frame(self, alias: str) -> pl.DataFrame:
        """DataFrame normalizado, ordenado por hora del evento y sin duplicados."""
        import numpy as np

        data = {
            "alias": pl.Series([alias] * len(self), dtype=pl.String),
            "event_time": pl.from_epoch(pl.Series(np.frombuffer(self.epoch, dtype=np.int64).copy()), time_unit="s")
            .dt.cast_time_unit("us")
            .dt.replace_time_zone("UTC"),
        }
        for key, arr in self.cols.items():
            data[key] = pl.Series(np.frombuffer(arr, dtype=np.float64).copy()).fill_nan(None)
        data["engine_on"] = pl.Series(np.frombuffer(self.engine_on, dtype=np.int8) == 1)
        data["provenance"] = pl.Series([PROVENANCE] * len(self), dtype=pl.String)
        df = pl.DataFrame(data).select(NORMALIZED_COLUMNS)
        return df.unique(subset=["event_time"], keep="first", maintain_order=True).sort("event_time")


def to_csv_frame(df: pl.DataFrame) -> pl.DataFrame:
    """Formato de texto estable (hora ISO-8601 con Z) para CSV y fixtures."""
    return df.with_columns(pl.col("event_time").dt.strftime("%Y-%m-%dT%H:%M:%SZ"))
