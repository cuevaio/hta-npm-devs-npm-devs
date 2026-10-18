"""Geometría de los corredores (tabla `corridors`, cargada desde corridors.json del pipeline)."""

import json

import psycopg

from .schemas import Corredor, CorridorList

_CORRIDORS = """
SELECT corridor, via, origin_terminal, dest_terminal, km, ST_AsGeoJSON(geom, 6) FROM corridors ORDER BY corridor
"""


def corridor_list(database_url: str) -> CorridorList:
    with psycopg.connect(database_url) as conn:
        rows = conn.execute(_CORRIDORS).fetchall()
    return CorridorList(corredores=[
        Corredor(corredor=c, via=v, origen=o, destino=d, largo_km=km, coordenadas=json.loads(g)["coordinates"])
        for c, v, o, d, km, g in rows
    ])
