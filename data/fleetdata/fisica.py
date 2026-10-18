"""Modelo físico de un tractocamión sobre una ruta (telemetría `synthetic_demo`, ADR 0012).

Perfil de velocidad sobre la malla de distancia de la ruta (límite de vía, curvas, potencia disponible en
subida, freno motor en bajada, aceleración y frenado acotados) y consumo por potencia en rueda:

    F = m·a + m·g·(Crr + pendiente) + ½·ρ(h)·CdA·v²      L/h = ralentí + P⁺/η · BSFC(h) / 835 g/L

Calibrado contra lo medido en FEAD ([fead-ems-dataset2-perfil.md]): unos 33 L/100 km a 80 km/h en llano
con 40 t y una mediana cercana a 21,6 L/h. La altitud resta potencia al motor y aire a la resistencia.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .rutas import Ruta

G = 9.81
DIESEL_G_L = 835.0
ETA = 0.92  # transmisión
PENDIENTE_MAX = 0.09
A_LAT = 1.4  # m/s² en curva para un camión cargado
DECEL = 0.5  # m/s²
V_MIN = 0.5  # m/s en una parada
TRAMO_URBANO_KM = 12.0
V_URBANA = 40 / 3.6


@dataclass(frozen=True)
class Camion:
    tara_t: float = 15.5
    cda_m2: float = 5.8
    crr: float = 0.0058
    p_max_kw: float = 320.0
    bsfc_g_kwh: float = 205.0
    ralenti_lph: float = 2.4
    condicion: float = 1.0  # >1: el vehículo gasta más por su estado (llantas, inyectores)


@dataclass(frozen=True)
class Manejo:
    v_crucero_kmh: float = 82.0
    acel_ms2: float = 0.35


def rho(alt_m: np.ndarray) -> np.ndarray:
    return 1.225 * np.exp(-alt_m / 8500)


def potencia_kw(alt_m: np.ndarray, camion: Camion) -> np.ndarray:
    """Un turbodiésel pierde ~0,7 % de potencia por cada 100 m sobre 1 500 m."""
    return camion.p_max_kw * (1 - 0.007 * np.maximum(0.0, alt_m - 1500) / 100)


def bsfc(alt_m: np.ndarray, camion: Camion) -> np.ndarray:
    return camion.bsfc_g_kwh * (1 + 0.02 * np.maximum(0.0, alt_m) / 1000)


def pendiente(ruta: Ruta) -> np.ndarray:
    g = np.gradient(ruta.alt_m, ruta.km * 1000)
    return np.clip(g, -PENDIENTE_MAX, PENDIENTE_MAX)


def radio_m(ruta: Ruta) -> np.ndarray:
    """Radio de curva aproximado con el cambio de rumbo entre puntos vecinos."""
    y = np.radians(ruta.lat)
    x = np.radians(ruta.lon) * np.cos(y)
    rumbo = np.unwrap(np.arctan2(np.gradient(y), np.gradient(x)))
    giro = np.abs(np.gradient(rumbo, ruta.km * 1000))
    return 1 / np.maximum(giro, 1e-6)


def _v_subida(masa_kg, pend, alt, camion: Camion) -> np.ndarray:
    """Velocidad sostenible con el 85 % de la potencia: m·g·(Crr+p)·v + ½ρCdA·v³ = P (bisección)."""
    p = 0.85 * potencia_kw(alt, camion) * 1000 * ETA
    a, b = np.full_like(alt, 0.5), np.full_like(alt, 40.0)
    for _ in range(40):
        v = (a + b) / 2
        f = masa_kg * G * (camion.crr + pend) * v + 0.5 * rho(alt) * camion.cda_m2 * v**3 - p
        a, b = np.where(f > 0, a, v), np.where(f > 0, v, b)
    return a


def limite(ruta: Ruta, masa_t: float, camion: Camion, manejo: Manejo, paradas_km=(), lentos=()) -> np.ndarray:
    """Velocidad máxima (m/s) en cada punto de la ruta."""
    pend, alt = pendiente(ruta), ruta.alt_m
    v = np.full(len(ruta.km), manejo.v_crucero_kmh / 3.6)
    v = np.minimum(v, np.sqrt(A_LAT * radio_m(ruta)))
    v = np.minimum(v, _v_subida((camion.tara_t + masa_t) * 1000, pend, alt, camion))
    v = np.where(pend < -0.04, np.minimum(v, 55 / 3.6), v)  # freno motor en bajada
    v = np.where(pend < -0.06, np.minimum(v, 38 / 3.6), v)
    urbano = (ruta.km < TRAMO_URBANO_KM) | (ruta.km > ruta.largo_km - TRAMO_URBANO_KM)
    v = np.where(urbano, np.minimum(v, V_URBANA), v)
    for km0, km1, f in lentos:  # tráfico u obras
        v = np.where((ruta.km >= km0) & (ruta.km < km1), v * f, v)
    v = np.maximum(v, 4.0)
    v[0] = v[-1] = V_MIN
    for km in paradas_km:
        v[min(np.searchsorted(ruta.km, km), len(v) - 1)] = V_MIN
    return v


def perfil(ruta: Ruta, masa_t: float, camion: Camion, manejo: Manejo, paradas_km=(), lentos=()):
    """Velocidad (m/s), consumo (L/h), carga del motor (0-1) y duración (s) de cada paso de la malla."""
    vlim = limite(ruta, masa_t, camion, manejo, paradas_km, lentos)
    ds = np.diff(ruta.km) * 1000
    m = (camion.tara_t + masa_t) * 1000
    pend, alt = pendiente(ruta), ruta.alt_m
    pmax = potencia_kw(alt, camion) * 1000 * ETA
    v = vlim.copy()
    for i in range(len(ds)):  # aceleración acotada por el manejo y por la potencia
        resist = m * G * (camion.crr + pend[i]) + 0.5 * rho(alt[i]) * camion.cda_m2 * v[i] ** 2
        a = min(manejo.acel_ms2, max(0.02, (pmax[i] / max(v[i], 1.0) - resist) / m))
        v[i + 1] = min(v[i + 1], np.sqrt(v[i] ** 2 + 2 * a * ds[i]))
    for i in range(len(ds) - 1, -1, -1):  # frenado anticipado
        v[i] = min(v[i], np.sqrt(v[i + 1] ** 2 + 2 * DECEL * ds[i]))
    vm = (v[:-1] + v[1:]) / 2
    dt = ds / np.maximum(vm, 0.3)
    acc = (v[1:] ** 2 - v[:-1] ** 2) / (2 * ds)
    f = m * acc + m * G * (camion.crr + pend[:-1]) + 0.5 * rho(alt[:-1]) * camion.cda_m2 * vm**2
    p_kw = f * vm / ETA / 1000
    lph = np.where(p_kw > 0, camion.ralenti_lph + p_kw * bsfc(alt[:-1], camion) / DIESEL_G_L, 0.4)
    carga = np.clip(p_kw / (pmax[:-1] / ETA / 1000), 0, 1)
    return vm, lph * camion.condicion, carga, dt
