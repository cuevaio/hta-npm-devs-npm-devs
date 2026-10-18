"""Corredores de Perú sobre carreteras reales (ADR 0012).

La geometría sale de OpenStreetMap vía OSRM (© colaboradores de OpenStreetMap, ODbL) y la altitud de
SRTM 90 m vía OpenTopoData (dominio público). Se descargan una sola vez con

    uv run python -m fleetdata.rutas

y quedan versionadas en `rutas_peru.json`, remuestreadas cada `PASO_M` metros. El generador nunca
toca la red.
"""
from __future__ import annotations

import json
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .trips import haversine_km

RUTAS_JSON = Path(__file__).with_name("rutas_peru.json")
PASO_M = 100
OSRM = "https://router.project-osrm.org/route/v1/driving/{coords}?overview=full&geometries=geojson"
TOPO = "https://api.opentopodata.org/v1/srtm90m?locations={locs}"

# Terminales: zonas industriales de cada ciudad (coordenadas aproximadas).
TERMINALES = {
    "LIM": ("Lima", -12.0500, -77.0900),
    "AQP": ("Arequipa", -16.4100, -71.5300),
    "HYO": ("Huancayo", -12.0560, -75.2150),
    "PIU": ("Piura", -5.1950, -80.6400),
    "JUL": ("Juliaca", -15.4900, -70.1350),
}

# Corredor -> (vía, terminal de ida, terminal de vuelta). La ida sale del primer terminal.
CORREDORES = {
    "LIM-AQP": ("Panamericana Sur", "LIM", "AQP"),
    "LIM-HYO": ("Carretera Central", "LIM", "HYO"),
    "LIM-PIU": ("Panamericana Norte", "LIM", "PIU"),
    "AQP-JUL": ("Arequipa–Juliaca (PE-34A)", "AQP", "JUL"),
}


@dataclass(frozen=True)
class Ruta:
    """Ruta de ida remuestreada: km acumulado, posición y altitud suavizada por punto."""

    corredor: str
    km: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    alt_m: np.ndarray

    @property
    def largo_km(self) -> float:
        return float(self.km[-1])

    def invertida(self) -> "Ruta":
        """La misma ruta recorrida en sentido vuelta."""
        return Ruta(self.corredor, self.largo_km - self.km[::-1], self.lat[::-1], self.lon[::-1], self.alt_m[::-1])


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "fleet-intelligence-demo/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def _remuestrear(lat: np.ndarray, lon: np.ndarray, paso_km: float):
    seg = haversine_km(lat[:-1], lon[:-1], lat[1:], lon[1:])
    acum = np.concatenate(([0.0], np.cumsum(seg)))
    km = np.arange(0.0, acum[-1], paso_km)
    return km, np.interp(km, acum, lat), np.interp(km, acum, lon)


def _altitudes(lat: np.ndarray, lon: np.ndarray) -> list[float]:
    out: list[float] = []
    for i in range(0, len(lat), 100):  # OpenTopoData: 100 puntos y 1 llamada por segundo
        locs = "|".join(f"{a:.5f},{b:.5f}" for a, b in zip(lat[i : i + 100], lon[i : i + 100]))
        res = _get_json(TOPO.format(locs=locs))["results"]
        out += [r["elevation"] if r["elevation"] is not None else float("nan") for r in res]
        time.sleep(1.1)
    return out


def descargar(destino: Path = RUTAS_JSON) -> dict:
    rutas = {}
    for corredor, (via, a, b) in CORREDORES.items():
        (_, la, oa), (_, lb, ob) = TERMINALES[a], TERMINALES[b]
        geo = _get_json(OSRM.format(coords=f"{oa},{la};{ob},{lb}"))["routes"][0]["geometry"]["coordinates"]
        lon, lat = np.array(geo).T
        km, lat, lon = _remuestrear(lat, lon, PASO_M / 1000)
        alt = np.array(_altitudes(lat, lon))
        alt = np.interp(np.arange(len(alt)), np.flatnonzero(~np.isnan(alt)), alt[~np.isnan(alt)])
        rutas[corredor] = {"via": via, "paso_m": PASO_M, "lat": np.round(lat, 5).tolist(),
                           "lon": np.round(lon, 5).tolist(), "alt_m": np.round(alt).astype(int).tolist()}
        print(f"{corredor}: {km[-1]:.0f} km, {len(km)} puntos, altitud {alt.min():.0f}-{alt.max():.0f} m")
    doc = {"fuente": "OpenStreetMap vía OSRM (ODbL) y SRTM 90 m vía OpenTopoData", "rutas": rutas}
    destino.write_text(json.dumps(doc, separators=(",", ":")))
    return doc


def _suavizar(alt: np.ndarray, ventana: int) -> np.ndarray:
    """Media móvil: SRTM sobre una carretera trae saltos de cortes y quebradas."""
    k = np.ones(ventana) / ventana
    pad = np.pad(alt, ventana // 2, mode="edge")
    return np.convolve(pad, k, mode="valid")[: len(alt)]


def cargar(path: Path = RUTAS_JSON) -> dict[str, Ruta]:
    doc = json.loads(path.read_text())["rutas"]
    out = {}
    for corredor, r in doc.items():
        lat, lon = np.array(r["lat"]), np.array(r["lon"])
        km = np.arange(len(lat)) * r["paso_m"] / 1000
        alt = _suavizar(np.array(r["alt_m"], dtype=float), 21)  # ~2 km
        out[corredor] = Ruta(corredor, km, lat, lon, alt)
    return out


if __name__ == "__main__":
    descargar()
