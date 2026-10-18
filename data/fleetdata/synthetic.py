"""Logística sintética determinista de la demo (procedencia `synthetic_demo`).

Un flete por viaje (1:1), con conductores y clientes ficticios. Los reportes del conductor de este
módulo son guionados y precargados: su procedencia es `synthetic_demo`. Un reporte escrito en vivo por
WhatsApp durante la demo es `human_reported` (CONTEXT.md); el flete y el conductor siguen siendo sintéticos.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import polars as pl

PROVENANCE = "synthetic_demo"
SEED = 2020
FIRST_FREIGHT = 101

DRIVER_NAMES = [
    "Marcos Quispe", "Luis Valdivia", "Jorge Salas", "Pedro Herrera", "Ricardo Tello", "Andrés Paredes",
    "Hugo Montalvo", "César Lazo", "Iván Rojas", "Daniel Aguirre", "Walter Chávez", "Óscar Medina",
]
CLIENTS = ["Distribuidora Andina", "Aceros del Norte", "Agroexport Sur", "Lácteos Pampa", "Textiles Horizonte", "Cementos Meridian"]
CARGO = ["Abarrotes paletizados", "Perfiles de acero", "Insumos agrícolas", "Lácteos refrigerados", "Textil en fardos", "Cemento en bolsas"]

# Reportes guionados para el caso de la demo: (alias, hora local UTC+8 del evento, texto).
# Se asocian al viaje que cubre esa hora, al que arranca en las 6 h siguientes o, si no hay, al más cercano.
SCRIPTED_REPORTS = [
    ("T04", "2020-04-07 19:50", "Estoy detenido con el motor encendido calentando la cabina, hace mucho frío. Salgo en unos minutos."),
    ("T03", "2020-04-04 02:10", "Esperando que termine la carga en el terminal, dejé el motor en marcha para no perder la calefacción."),
    ("T07", "2020-04-08 06:55", "Subiendo la montaña con carga completa, voy lento y con el acelerador a fondo."),
    ("T28", "2020-04-07 08:40", "Mucho tráfico y neblina en la bajada, voy despacio."),
]
GENERIC_REPORTS = [
    "Todo en orden, sigo la ruta.",
    "Paré a descansar y cargar combustible, retomo en 30 minutos.",
    "Hay tráfico lento por obras en la carretera.",
]

FREIGHT_COLUMNS = ("freight_id", "trip_id", "alias", "driver_id", "client", "cargo", "corridor", "sentido",
                   "origin_terminal", "dest_terminal", "planned_departure", "provenance")
DRIVER_COLUMNS = ("driver_id", "name", "provenance")
REPORT_COLUMNS = ("report_id", "trip_id", "driver_id", "reported_at", "text", "provenance")


def _iso(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _local_to_epoch(s: str) -> int:
    return int((datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone(timedelta(hours=8)))).timestamp())


def generate(trips: pl.DataFrame, seed: int = SEED) -> dict[str, pl.DataFrame]:
    """`trips` necesita trip_id, alias, corridor, sentido, origin_terminal, dest_terminal, t_start, t_end."""
    rng = random.Random(seed)
    rows = trips.sort(["t_start", "alias", "trip_id"]).to_dicts()
    drivers = [{"driver_id": f"D-{i:02d}", "name": n, "provenance": PROVENANCE} for i, n in enumerate(DRIVER_NAMES, 1)]
    by_alias: dict[str, str] = {}
    freights, reports = [], []
    for i, tr in enumerate(rows):
        # cada vehículo tiene un conductor habitual (relevo ocasional)
        home = by_alias.setdefault(tr["alias"], drivers[rng.randrange(len(drivers))]["driver_id"])
        driver = home if rng.random() < 0.8 else drivers[rng.randrange(len(drivers))]["driver_id"]
        k = rng.randrange(len(CLIENTS))
        freights.append(
            {
                "freight_id": f"F-{FIRST_FREIGHT + i}",
                "trip_id": tr["trip_id"],
                "alias": tr["alias"],
                "driver_id": driver,
                "client": CLIENTS[k],
                "cargo": CARGO[rng.randrange(len(CARGO))],
                "corridor": tr["corridor"],
                "sentido": tr["sentido"],
                "origin_terminal": tr["origin_terminal"],
                "dest_terminal": tr["dest_terminal"],
                "planned_departure": _iso(tr["t_start"]),
                "provenance": PROVENANCE,
            }
        )
        # un reporte genérico a mitad de viaje, de vez en cuando
        if rng.random() < 0.5:
            reports.append({"trip_id": tr["trip_id"], "driver_id": driver,
                            "reported_at": _iso((tr["t_start"] + tr["t_end"]) // 2),
                            "text": rng.choice(GENERIC_REPORTS), "provenance": PROVENANCE})
    driver_of = {f["trip_id"]: f["driver_id"] for f in freights}
    for alias, local, text in SCRIPTED_REPORTS:
        at = _local_to_epoch(local)
        mine = [tr for tr in rows if tr["alias"] == alias]
        if not mine:
            continue
        # el viaje que cubre la hora (o arranca en las 6 h siguientes); si no hay, el más cercano
        gap = lambda tr: max(tr["t_start"] - 6 * 3600 - at, at - tr["t_end"], 0)
        tr = min(mine, key=lambda tr: (gap(tr), tr["t_start"]))
        reports.append({"trip_id": tr["trip_id"], "driver_id": driver_of[tr["trip_id"]],
                        "reported_at": _iso(at), "text": text, "provenance": PROVENANCE})
    reports.sort(key=lambda r: (r["reported_at"], r["trip_id"]))
    for n, r in enumerate(reports, 1):
        r["report_id"] = f"R-{n:03d}"
    used = {f["driver_id"] for f in freights}
    return {
        "freights": pl.DataFrame(freights, schema={c: pl.String for c in FREIGHT_COLUMNS}),
        "drivers": pl.DataFrame([d for d in drivers if d["driver_id"] in used], schema={c: pl.String for c in DRIVER_COLUMNS}),
        "driver_reports": pl.DataFrame(reports, schema={c: pl.String for c in REPORT_COLUMNS}).select(REPORT_COLUMNS),
    }
