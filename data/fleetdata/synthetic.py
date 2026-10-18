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
CLIENTS = ["Distribuidora Andina S.A.C.", "Aceros del Norte S.A.", "Agroexport Sur S.A.C.", "Lácteos Pampa S.A.",
           "Textiles Horizonte S.A.C.", "Cementos Meridian S.A.A."]
CARGO = ["Abarrotes paletizados", "Perfiles de acero", "Insumos agrícolas", "Lácteos refrigerados", "Textil en fardos", "Cemento en bolsas"]

# Supuestos comerciales de la demo (no son tarifas de mercado verificadas): S/ por tonelada-km sin IGV.
TARIFA_PEN_TKM = {"LIM-AQP": 0.17, "LIM-PIU": 0.17, "LIM-HYO": 0.30, "AQP-JUL": 0.28}
TARIFA_PEN_TKM_DEFAULT = 0.18
CARGA_MIN_T = 10.0  # se cobra como mínimo esta carga
IGV = 0.18
# Detracción del transporte de bienes: 4 % si la operación supera S/ 400 (docs/analisis-facturacion-transporte-peru.md).
DETRACCION = 0.04
DETRACCION_DESDE_PEN = 400.0
PRECIO_DIESEL_PEN_L = 4.30  # supuesto (~S/ 16,3 por galón)

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

FREIGHT_COLUMNS = ("freight_id", "trip_id", "alias", "driver_id", "client", "client_ruc", "cargo", "tonnage_t",
                   "corridor", "sentido", "origin_terminal", "dest_terminal", "planned_departure", "gre_remitente",
                   "gre_transportista", "tarifa_pen", "igv_pen", "total_pen", "detraccion_pen", "fuel_liters",
                   "fuel_cost_pen", "provenance")
FLOAT_COLUMNS = ("tonnage_t", "tarifa_pen", "igv_pen", "total_pen", "detraccion_pen", "fuel_liters", "fuel_cost_pen")
DRIVER_COLUMNS = ("driver_id", "name", "provenance")
REPORT_COLUMNS = ("report_id", "trip_id", "driver_id", "reported_at", "text", "provenance")


def _iso(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _local_to_epoch(s: str) -> int:
    return int((datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone(timedelta(hours=8)))).timestamp())


def ruc_ficticio(rng: random.Random) -> str:
    """RUC de empresa (20…) con el dígito verificador mal a propósito: no puede ser el de nadie."""
    base = "20" + "".join(str(rng.randrange(10)) for _ in range(8))
    resto = sum(int(d) * w for d, w in zip(base, (5, 4, 3, 2, 7, 6, 5, 4, 3, 2))) % 11
    valido = (11 - resto) % 10
    return base + str((valido + 1) % 10)


def comercial(corridor: str, tonnage_t: float, km: float, liters: float | None) -> dict:
    tarifa = round(max(tonnage_t, CARGA_MIN_T) * km * TARIFA_PEN_TKM.get(corridor, TARIFA_PEN_TKM_DEFAULT), -1)
    igv = round(tarifa * IGV, 2)
    total = tarifa + igv
    return {
        "tarifa_pen": tarifa, "igv_pen": igv, "total_pen": total,
        "detraccion_pen": round(total * DETRACCION, 2) if total > DETRACCION_DESDE_PEN else 0.0,
        "fuel_liters": liters, "fuel_cost_pen": round(liters * PRECIO_DIESEL_PEN_L, 2) if liters is not None else None,
    }


def generate(trips: pl.DataFrame, seed: int = SEED, reportes: list[dict] | None = None) -> dict[str, pl.DataFrame]:
    """`trips` necesita trip_id, alias, corridor, sentido, origin_terminal, dest_terminal, t_start, t_end.

    Opcionales: carga_t (t), km_ruta o km y liters (consumo observado del viaje). `reportes` reemplaza a los
    guionados de FEAD: [{trip_id, at (epoch s), text}].
    """
    rng = random.Random(seed)
    clients = [(c, ruc_ficticio(rng)) for c in CLIENTS]
    rows = trips.sort(["t_start", "alias", "trip_id"]).to_dicts()
    drivers = [{"driver_id": f"D-{i:02d}", "name": n, "provenance": PROVENANCE} for i, n in enumerate(DRIVER_NAMES, 1)]
    by_alias: dict[str, str] = {}
    freights, reports = [], []
    for i, tr in enumerate(rows):
        # cada vehículo tiene un conductor habitual (relevo ocasional)
        home = by_alias.setdefault(tr["alias"], drivers[rng.randrange(len(drivers))]["driver_id"])
        driver = home if rng.random() < 0.8 else drivers[rng.randrange(len(drivers))]["driver_id"]
        k = rng.randrange(len(clients))
        client, ruc = clients[k]
        cargo = CARGO[k]  # cada cliente despacha su propia carga
        tonnage = tr.get("carga_t") or round(rng.uniform(12, 30), 1)
        km = tr.get("km") or tr.get("km_ruta") or 0.0
        freights.append(
            {
                "freight_id": f"F-{FIRST_FREIGHT + i}",
                "trip_id": tr["trip_id"],
                "alias": tr["alias"],
                "driver_id": driver,
                "client": client,
                "client_ruc": ruc,
                "cargo": cargo,
                "tonnage_t": float(tonnage),
                "corridor": tr["corridor"],
                "sentido": tr["sentido"],
                "origin_terminal": tr["origin_terminal"],
                "dest_terminal": tr["dest_terminal"],
                "planned_departure": _iso(tr["t_start"]),
                "gre_remitente": f"T001-{rng.randrange(1, 99999):08d}",
                "gre_transportista": f"V001-{i + 1:08d}",
                **comercial(tr["corridor"], float(tonnage), float(km), tr.get("liters")),
                "provenance": PROVENANCE,
            }
        )
        # un reporte genérico a mitad de viaje, de vez en cuando
        if rng.random() < 0.5:
            reports.append({"trip_id": tr["trip_id"], "driver_id": driver,
                            "reported_at": _iso((tr["t_start"] + tr["t_end"]) // 2),
                            "text": rng.choice(GENERIC_REPORTS), "provenance": PROVENANCE})
    driver_of = {f["trip_id"]: f["driver_id"] for f in freights}
    for r in reportes or []:
        reports.append({"trip_id": r["trip_id"], "driver_id": driver_of[r["trip_id"]], "reported_at": _iso(r["at"]),
                        "text": r["text"], "provenance": PROVENANCE})
    for alias, local, text in SCRIPTED_REPORTS if reportes is None else []:
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
        "freights": pl.DataFrame(freights, schema={c: pl.Float64 if c in FLOAT_COLUMNS else pl.String for c in FREIGHT_COLUMNS}),
        "drivers": pl.DataFrame([d for d in drivers if d["driver_id"] in used], schema={c: pl.String for c in DRIVER_COLUMNS}),
        "driver_reports": pl.DataFrame(reports, schema={c: pl.String for c in REPORT_COLUMNS}).select(REPORT_COLUMNS),
    }
