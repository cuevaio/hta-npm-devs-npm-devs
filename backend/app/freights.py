"""Tablero de fletes: capa comercial peruana (ADR 0012) cruzada con el consumo observado de cada viaje.

Solo los fletes cuyo viaje ya terminó a la hora del replay suman ingresos, combustible y margen: el
replay nunca revela consumo futuro.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.rows import dict_row

from .schemas import AgregadoFletes, FleteDetalle, FreightBoard, ResumenFletes

LIMA = timezone(timedelta(hours=-5))

_FREIGHTS = """
SELECT f.freight_id, f.trip_id, f.alias, d.name AS driver, f.client, f.client_ruc, f.cargo, f.tonnage_t,
       t.corridor, t.sentido, t.origin_terminal, t.dest_terminal, t.t_start, t.t_end,
       f.gre_remitente, f.gre_transportista, f.tarifa_pen::float, f.igv_pen::float, f.total_pen::float,
       f.detraccion_pen::float, t.km, coalesce(t.liters, f.fuel_liters) AS liters,
       f.fuel_cost_pen::float
FROM freights f
JOIN trips t ON t.trip_id = f.trip_id
LEFT JOIN drivers d ON d.driver_id = f.driver_id
ORDER BY t.t_start, f.freight_id
"""


def _estado(row: dict, hora: datetime) -> str:
    if row["t_start"] > hora:
        return "programado"
    return "finalizado" if row["t_end"] <= hora else "en_curso"


def _detalle(row: dict, hora: datetime) -> FleteDetalle:
    estado = _estado(row, hora)
    fin = estado == "finalizado"
    km, litros, costo = (row["km"], row["liters"], row["fuel_cost_pen"]) if fin else (None, None, None)
    return FleteDetalle(
        flete_id=row["freight_id"], viaje_id=row["trip_id"], vehiculo=row["alias"], conductor=row["driver"],
        cliente=row["client"], ruc_cliente=row["client_ruc"], carga=row["cargo"], toneladas=row["tonnage_t"],
        corredor=row["corridor"], sentido=row["sentido"], origen=row["origin_terminal"], destino=row["dest_terminal"],
        salida=row["t_start"], llegada=row["t_end"] if fin else None, estado=estado,
        gre_remitente=row["gre_remitente"], gre_transportista=row["gre_transportista"],
        tarifa_pen=row["tarifa_pen"], igv_pen=row["igv_pen"], total_pen=row["total_pen"],
        detraccion_pen=row["detraccion_pen"], km=km, litros=litros,
        l_100km=round(litros / km * 100, 2) if km and litros is not None else None,
        combustible_pen=costo,
        margen_pen=round(row["tarifa_pen"] - costo, 2) if costo is not None and row["tarifa_pen"] is not None else None,
    )


def _agregar(clave: str, fletes: list[FleteDetalle]) -> dict:
    ingresos = sum(f.tarifa_pen or 0 for f in fletes)
    combustible = sum(f.combustible_pen or 0 for f in fletes)
    km = sum(f.km or 0 for f in fletes)
    litros = sum(f.litros or 0 for f in fletes)
    margen = ingresos - combustible
    return dict(
        clave=clave, fletes=len(fletes), toneladas=round(sum(f.toneladas or 0 for f in fletes), 1),
        ingresos_pen=round(ingresos, 2), combustible_pen=round(combustible, 2), margen_pen=round(margen, 2),
        margen_pct=round(margen / ingresos * 100, 1) if ingresos else None,
        l_100km=round(litros / km * 100, 2) if km else None,
    )


def _por(fletes: list[FleteDetalle], key) -> list[AgregadoFletes]:
    grupos: dict[str, list[FleteDetalle]] = defaultdict(list)
    for f in fletes:
        grupos[key(f)].append(f)
    return [AgregadoFletes(**_agregar(k, v)) for k, v in sorted(grupos.items())]


def freight_board(database_url: str) -> tuple[FreightBoard, datetime, datetime, datetime]:
    """Devuelve (datos, desde, hasta, actualizado_en); desde/hasta en hora del evento."""
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        st = conn.execute("SELECT * FROM replay_state").fetchone()
        rows = conn.execute(_FREIGHTS).fetchall()
    hora = st["hora_replay"]
    fletes = [_detalle(r, hora) for r in rows]
    fin = [f for f in fletes if f.estado == "finalizado"]
    resumen = ResumenFletes(
        **_agregar("total", fin),
        en_curso=sum(f.estado == "en_curso" for f in fletes),
        programados=sum(f.estado == "programado" for f in fletes),
        igv_pen=round(sum(f.igv_pen or 0 for f in fin), 2),
        detraccion_pen=round(sum(f.detraccion_pen or 0 for f in fin), 2),
        litros=round(sum(f.litros or 0 for f in fin), 1),
        km=round(sum(f.km or 0 for f in fin), 1),
    )
    data = FreightBoard(
        resumen=resumen,
        por_corredor=_por(fin, lambda f: f.corredor),
        por_cliente=_por(fin, lambda f: f.cliente),
        por_vehiculo=_por(fin, lambda f: f.vehiculo),
        por_dia=_por(fin, lambda f: f.llegada.astimezone(LIMA).date().isoformat()),
        fletes=fletes,
    )
    desde = min([st["inicio"], *(r["t_start"] for r in rows)])
    return data, desde, hora, st["updated_at"]
