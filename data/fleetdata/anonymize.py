"""Sustituye hash -> alias y descarta todo dato personal.

Se conservan lat/lon (son las trayectorias que muestra la demo, ADR 0006). Se descartan
hash de vehículo, IMEI, matrícula y direcciones textuales. La tabla de alias nunca se escribe.
"""
from __future__ import annotations

from collections.abc import Iterable, Iterator

KEPT_FIELDS = ("alias", "ems_time", "signals", "lat", "lon")


def anonymize_row(row: dict, alias_map: dict[str, str]) -> dict:
    return {
        "alias": alias_map[row["truck_hash"]],
        "ems_time": row["ems_time"],
        "signals": row["signals"],
        "lat": row["lat"],
        "lon": row["lon"],
    }


def anonymize(rows: Iterable[dict], alias_map: dict[str, str]) -> Iterator[dict]:
    for row in rows:
        if row["truck_hash"] in alias_map:
            yield anonymize_row(row, alias_map)
