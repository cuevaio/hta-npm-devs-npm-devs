"""Extracción en streaming de los vehículos pedidos desde el tar.gz de FEAD EMS-2.

Nunca descomprime el archivo a disco: lee `ems_yingche_YYYYMMDD.txt` miembro a miembro.
Cada fila trae 24 campos separados por tabulación (ver docs/research/fead-ems-dataset2-perfil.md §2.1).
Las filas que salen de aquí todavía llevan datos personales (hash, IMEI, matrícula, dirección):
`anonymize.anonymize` los descarta antes de que nada se guarde.
"""
from __future__ import annotations

import json
import re
import tarfile
from collections.abc import Iterable, Iterator
from pathlib import Path

N_FIELDS = 24
MEMBER_RE = re.compile(r"ems_yingche_(\d{8})\.txt$")

# Alias de la flota analizada (T01…T28). La tabla de alias puede traer alguno más, de relleno.
FLEET_ALIASES = tuple(f"T{i:02d}" for i in range(1, 29))
# Vehículos de la demo (D33, ADR 0009).
DEMO_ALIASES = ("T03", "T04", "T07", "T22", "T28", "T09")


def load_alias_map(path: Path) -> dict[str, str]:
    """Lee la tabla privada hash -> alias. Se recibe siempre por argumento."""
    with open(path, encoding="utf-8") as f:
        table = json.load(f)
    return {str(h): str(a) for h, a in table.items()}


def select_hashes(alias_map: dict[str, str], aliases: Iterable[str]) -> dict[str, str]:
    wanted = set(aliases)
    return {h: a for h, a in alias_map.items() if a in wanted}


def iter_rows(archive: Path, hashes: Iterable[str]) -> Iterator[dict]:
    """Filas crudas de los vehículos cuyo hash está en `hashes`, de todos los días del tar."""
    keep = {h.encode() for h in hashes}
    with tarfile.open(archive, "r|gz") as tar:
        for member in tar:
            if not member.isfile() or not MEMBER_RE.search(member.name):
                continue
            f = tar.extractfile(member)
            if f is None:
                continue
            for line in f:
                p = line.rstrip(b"\r\n").split(b"\t")
                if len(p) != N_FIELDS or p[8] not in keep:
                    continue
                try:
                    signals = json.loads(p[1])
                except ValueError:
                    continue
                yield {
                    "truck_hash": p[8].decode(),
                    "ems_time": p[5].decode(),
                    "signals": signals,
                    "lat": p[13].decode(),
                    "lon": p[14].decode(),
                    # Campos personales: solo para que el test de anonimización pueda verlos pasar.
                    "imei": p[6].decode(),
                    "plate": p[11].decode("utf-8", "replace"),
                    "address": p[20].decode("utf-8", "replace"),
                }
