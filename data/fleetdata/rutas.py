"""Corredores de Perú sobre carreteras reales (ADR 0012).

La geometría sale de OpenStreetMap vía OSRM (© colaboradores de OpenStreetMap, ODbL) y la altitud de
SRTM 90 m vía OpenTopoData (dominio público). Se descargan una sola vez con

    uv run python -m fleetdata.rutas

y quedan versionadas en `rutas_peru.json`, remuestreadas cada `PASO_M` metros (malla de la física y
de la altitud). La línea completa de la vía (`linea`, simplificada a menos de `TOLERANCIA_M`) se guarda
aparte: las posiciones van sobre ella para que el camión no salga de la pista con zoom alto. El
generador nunca toca la red.
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
TOLERANCIA_M = 1.0  # Douglas-Peucker de la línea completa
BERMA_M = 6.0  # una parada queda a la derecha del sentido de marcha
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
    """Ruta de ida: malla remuestreada (km, posición, altitud suavizada) y la línea completa de la vía.

    El km de la malla se lleva a la línea completa en proporción a sus largos (la malla corta las curvas
    y es un poco más corta).
    """

    corredor: str
    km: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    alt_m: np.ndarray
    linea_lat: np.ndarray | None = None
    linea_lon: np.ndarray | None = None

    @property
    def largo_km(self) -> float:
        return float(self.km[-1])

    def invertida(self) -> "Ruta":
        """La misma ruta recorrida en sentido vuelta."""
        inv = lambda a: None if a is None else a[::-1]
        return Ruta(self.corredor, self.largo_km - self.km[::-1], self.lat[::-1], self.lon[::-1], self.alt_m[::-1],
                    inv(self.linea_lat), inv(self.linea_lon))

    def _linea(self):
        if self.linea_lat is None:
            return self.km, self.lat, self.lon
        seg = haversine_km(self.linea_lat[:-1], self.linea_lon[:-1], self.linea_lat[1:], self.linea_lon[1:])
        acum = np.concatenate(([0.0], np.cumsum(seg)))
        return acum * self.largo_km / acum[-1], self.linea_lat, self.linea_lon

    def punto(self, km):
        """Posición sobre la vía real para un km (o array de km) de la malla."""
        acum, lat, lon = self._linea()
        return np.interp(km, acum, lat), np.interp(km, acum, lon)

    def berma(self, km: float, metros: float = BERMA_M) -> tuple[float, float]:
        """Punto a `metros` a la derecha del sentido de marcha (donde se estaciona un camión)."""
        la, lo = self.punto(np.array([max(km - 0.02, 0.0), min(km + 0.02, self.largo_km)]))
        lat0, lon0 = self.punto(km)
        k = np.cos(np.radians(lat0))
        dy, dx = la[1] - la[0], (lo[1] - lo[0]) * k  # rumbo de la vía en grados "planos"
        n = np.hypot(dx, dy) or 1.0
        d = metros / 111_195.0
        return float(lat0 - dx / n * d), float(lon0 + dy / n * d / k)


def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "certera-demo/0.1"})
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


def simplificar(lat: np.ndarray, lon: np.ndarray, tolerancia_m: float = TOLERANCIA_M) -> np.ndarray:
    """Índices que conserva Douglas-Peucker (proyección local en metros, iterativo)."""
    k = np.cos(np.radians(lat.mean()))
    x, y = lon * 111_195.0 * k, lat * 111_195.0
    keep = np.zeros(len(lat), dtype=bool)
    keep[0] = keep[-1] = True
    pila = [(0, len(lat) - 1)]
    while pila:
        a, b = pila.pop()
        if b <= a + 1:
            continue
        dx, dy = x[b] - x[a], y[b] - y[a]
        norma = np.hypot(dx, dy) or 1e-9
        d = np.abs(dy * (x[a + 1 : b] - x[a]) - dx * (y[a + 1 : b] - y[a])) / norma
        i = int(np.argmax(d))
        if d[i] > tolerancia_m:
            m = a + 1 + i
            keep[m] = True
            pila += [(a, m), (m, b)]
    return np.flatnonzero(keep)


def descargar_lineas(destino: Path = RUTAS_JSON) -> dict:
    """Agrega a `rutas_peru.json` la línea completa de cada corredor (sin volver a pedir altitudes)."""
    doc = json.loads(destino.read_text())
    for corredor, (_, a, b) in CORREDORES.items():
        (_, la, oa), (_, lb, ob) = TERMINALES[a], TERMINALES[b]
        geo = _get_json(OSRM.format(coords=f"{oa},{la};{ob},{lb}"))["routes"][0]["geometry"]["coordinates"]
        lon, lat = np.array(geo).T
        idx = simplificar(lat, lon)
        doc["rutas"][corredor]["linea"] = {"tolerancia_m": TOLERANCIA_M, "lat": np.round(lat[idx], 6).tolist(),
                                           "lon": np.round(lon[idx], 6).tolist()}
        print(f"{corredor}: {len(lat)} vértices de OSRM -> {len(idx)}")
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
        linea = r.get("linea")
        out[corredor] = Ruta(corredor, km, lat, lon, alt,
                             np.array(linea["lat"]) if linea else None, np.array(linea["lon"]) if linea else None)
    return out


if __name__ == "__main__":
    import sys

    descargar_lineas() if "--lineas" in sys.argv else descargar()
