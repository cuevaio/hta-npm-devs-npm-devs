"""Descarga de FEAD EMS dataset-2 y verificación de su checksum (SHA-256).

El hash del tar fijado aquí no identifica vehículos: es el del archivo público.
"""
from __future__ import annotations

import hashlib
import shutil
import urllib.request
from pathlib import Path

# Enlace público del README de FEAD (sin registro). Google Drive devuelve el tar.gz
# de ~1,5 GB (`2020-04-20 第二批数据.gz`).
DATASET_URL = (
    "https://drive.usercontent.google.com/download"
    "?id=15Awwj26PE0MIGRUW1CiCO2xkP3j8-z2o&export=download&confirm=t"
)
DATASET_SHA256 = "84ddf7d89a4e1fee7723f89d964cb916eda47f6200dc401b1f6f6564251756e2"


class ChecksumError(RuntimeError):
    pass


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 22):
            h.update(chunk)
    return h.hexdigest()


def verify_checksum(path: Path, expected: str = DATASET_SHA256) -> None:
    actual = sha256_of(path)
    if actual != expected.lower():
        raise ChecksumError(
            f"SHA-256 de {path.name} no coincide: esperado {expected}, obtenido {actual}. "
            "Borra el archivo y vuelve a descargarlo."
        )


def ensure_archive(
    archive: Path, url: str = DATASET_URL, expected_sha256: str = DATASET_SHA256
) -> Path:
    """Reutiliza `archive` si existe; si no, lo descarga. Siempre verifica el checksum.

    Un archivo descargado que no coincide se borra antes de fallar.
    """
    archive = Path(archive)
    downloaded = False
    if not archive.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        tmp = archive.with_name(archive.name + ".part")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as r, open(tmp, "wb") as f:
            shutil.copyfileobj(r, f, 1 << 22)
        tmp.rename(archive)
        downloaded = True
    try:
        verify_checksum(archive, expected_sha256)
    except ChecksumError:
        if downloaded:
            archive.unlink(missing_ok=True)
        raise
    return archive
