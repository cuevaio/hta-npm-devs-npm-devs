"""Datos de ejemplo coherentes (sintéticos) para el contrato. Sin base de datos."""

import json
from datetime import UTC, datetime
from pathlib import Path

from .schemas import (
    AgregadoFletes, Corredor, CorridorList, FleteDetalle, FreightBoard, ResumenFletes,
    Alerta, Anomalia, Bottlenecks, CuelloDeBotella, Flete, FleetOverview, FuelAnalysis, LineaBase,
    Pasada, Posicion, Provenance, ReplayState, ReporteConductor, TimeRange, Tramo, TripStatus,
    MetricasPeriodo, VehicleMetrics, VehicleStatus, VehiculoResumen,
)


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


UPDATED_AT = utc(2020, 4, 14, 3, 30)
REPLAY_START = utc(2020, 4, 13, 0, 0)
REPLAY_END = utc(2020, 4, 19, 23, 59)
CORREDOR = "LIM-AQP"

PROVENANCE = [Provenance.synthetic_demo, Provenance.model_inferred]  # flota de Perú (ADR 0012)
PROVENANCE_ALERTS = [*PROVENANCE, Provenance.human_reported]

T0 = utc(2020, 4, 14, 0, 0)
NOW = utc(2020, 4, 14, 3, 30)

H3 = ["868e6a027ffffff", "868e6a177ffffff", "868e6a8dfffffff", "868e6a8efffffff"]


def _t(i: int, sentido="ida") -> Tramo:
    return Tramo(h3=H3[i], sentido=sentido)


def _pos(lat: float, lon: float) -> Posicion:
    return Posicion(lat=lat, lon=lon)


# altitud_m: SRTM del punto de rutas_peru.json más cercano a cada posición (todas a ≤ 1 km de su ruta)
VEHICLES = {
    "T03": VehiculoResumen(alias="T03", estado="en_viaje", viaje_id="V-001", velocidad_kmh=72.5, posicion=_pos(-15.4502, -74.86845), altitud_m=575.0, hora_evento=NOW),
    "T07": VehiculoResumen(alias="T07", estado="en_viaje", viaje_id="V-002", velocidad_kmh=64.0, posicion=_pos(-14.12562, -75.71631), altitud_m=407.0, hora_evento=NOW),
    "T28": VehiculoResumen(alias="T28", estado="detenido", velocidad_kmh=0.0, posicion=_pos(-15.49, -70.13), altitud_m=3831.0, hora_evento=NOW),
    "T04": VehiculoResumen(alias="T04", estado="ralenti", velocidad_kmh=0.0, posicion=_pos(-15.83621, -74.27996), altitud_m=23.0, hora_evento=NOW),
    "T22": VehiculoResumen(alias="T22", estado="detenido", velocidad_kmh=0.0, posicion=_pos(-12.06, -75.21), altitud_m=3266.0, hora_evento=NOW),
    "T09": VehiculoResumen(alias="T09", estado="detenido", velocidad_kmh=0.0, posicion=_pos(-12.05, -77.09), altitud_m=63.0, hora_evento=NOW),
}

REPORTE = ReporteConductor(
    texto="Hay obras en la Panamericana Sur a la altura de Chala, estamos parados hace media hora",
    recibido_en=utc(2020, 4, 14, 2, 40),
)

ANOMALIA = Anomalia(
    id="A-001", viaje_id="V-001", vehiculo_alias="T03", tramos=[_t(1), _t(2)], exceso_l=9.4,
    evidencia="Dos tramos seguidos con consumo >= 1,25 x mediana de sus pares y sobre el p90; ralentí de 21 min en el segundo.",
    detectada_en=utc(2020, 4, 14, 2, 55),
)

ALERTA = Alerta(
    id="AL-001", anomalia=ANOMALIA, enviada_en=utc(2020, 4, 14, 3, 0),
    mensaje="T03 gasta 9,4 L más que sus pares en dos tramos seguidos del viaje V-001.",
    reporte_conductor=REPORTE,
)

TRIPS = {
    "V-001": TripStatus(
        viaje_id="V-001", vehiculo_alias="T03", conductor="Marcos Quispe (sintético)",
        flete=Flete(id="F-101", carga="Autopartes", cliente="Cliente Demo S.A.", origen="LIM", destino="AQP"),
        corredor=CORREDOR, sentido="ida", estado="en_curso", inicio=utc(2020, 4, 13, 18, 0), distancia_km=520.4, progreso_pct=51.6,
    ),
    "V-002": TripStatus(
        viaje_id="V-002", vehiculo_alias="T07", conductor="Hugo Montalvo (sintético)",
        flete=Flete(id="F-102", carga="Electrodomésticos", cliente="Cliente Demo S.A.", origen="LIM", destino="AQP"),
        corredor=CORREDOR, sentido="ida", estado="en_curso", inicio=utc(2020, 4, 13, 20, 0), distancia_km=310.0, progreso_pct=30.7,
    ),
}


def _pasada(i, obs, base, ralenti=0.0):
    sobre = base is not None and obs >= 1.25 * base.mediana_l and obs > base.p90_l
    return Pasada(tramo=_t(i), consumo_observado_l=obs, linea_base=base, sobreconsumo=sobre,
                  exceso_l=None if base is None else round(obs - base.mediana_l, 1), ralenti_min=ralenti)


FUEL = {
    "V-001": FuelAnalysis(
        viaje_id="V-001", distancia_km=1840.5, consumo_observado_l=612.3, consumo_l_100km=33.3, exceso_total_l=9.4,
        pasadas=[
            _pasada(0, 5.1, LineaBase(mediana_l=5.0, p90_l=5.9, n_pasadas=14)),
            _pasada(1, 11.8, LineaBase(mediana_l=6.1, p90_l=7.0, n_pasadas=12), 4.0),
            _pasada(2, 9.9, LineaBase(mediana_l=7.0, p90_l=8.1, n_pasadas=11), 21.0),
            _pasada(3, 6.3, None),
        ],
        anomalias=[ANOMALIA],
    ),
    "V-002": FuelAnalysis(
        viaje_id="V-002", distancia_km=1320.0, consumo_observado_l=455.8, consumo_l_100km=34.5, exceso_total_l=0.0,
        pasadas=[
            _pasada(0, 5.0, LineaBase(mediana_l=5.0, p90_l=5.9, n_pasadas=14)),
            _pasada(1, 6.2, LineaBase(mediana_l=6.1, p90_l=7.0, n_pasadas=12), 2.0),
            _pasada(2, 7.1, LineaBase(mediana_l=7.0, p90_l=8.1, n_pasadas=11)),
        ],
        anomalias=[],
    ),
}

BOTTLENECKS = {
    "V-001": Bottlenecks(
        viaje_id="V-001", tiempo_perdido_min=62.0,
        cuellos_de_botella=[
            CuelloDeBotella(tipo="parada_sin_explicar", inicio=utc(2020, 4, 14, 1, 10), fin=utc(2020, 4, 14, 1, 52), duracion_min=42.0,
                            impacto_min=42.0, explicada=False, posicion=_pos(-15.6602, -74.6489)),
            CuelloDeBotella(tipo="ralenti_prolongado", inicio=utc(2020, 4, 14, 2, 20), fin=utc(2020, 4, 14, 2, 41), duracion_min=21.0,
                            impacto_min=20.0, explicada=True, reporte_conductor=REPORTE, posicion=_pos(-15.4502, -74.86845)),
        ],
    ),
    "V-002": Bottlenecks(
        viaje_id="V-002", tiempo_perdido_min=0.0,
        cuellos_de_botella=[
            CuelloDeBotella(tipo="parada_explicada", inicio=utc(2020, 4, 14, 0, 30), fin=utc(2020, 4, 14, 0, 55), duracion_min=25.0,
                            impacto_min=0.0, explicada=True, posicion=_pos(-14.8411, -74.9683)),
        ],
    ),
}

VEHICLE_STATUS = {
    "T03": VehicleStatus(**VEHICLES["T03"].model_dump(), corredor=CORREDOR, sentido="ida", conductor="Marcos Quispe (sintético)", ultima_alerta_id="AL-001"),
    "T07": VehicleStatus(**VEHICLES["T07"].model_dump(), corredor=CORREDOR, sentido="ida", conductor="Hugo Montalvo (sintético)"),
}
for _a, _v in VEHICLES.items():
    VEHICLE_STATUS.setdefault(_a, VehicleStatus(**_v.model_dump()))

FLEET = FleetOverview(total_vehiculos=len(VEHICLES), viajes_en_curso=len(TRIPS), alertas_abiertas=1, vehiculos=list(VEHICLES.values()))

INITIAL_REPLAY = ReplayState(estado="paused", velocidad=1.0, hora_replay=REPLAY_START, inicio=REPLAY_START, fin=REPLAY_END)


def range_from(*times: datetime) -> TimeRange:
    return TimeRange(from_=min(times), to=max(times))


# Tablero de fletes (flota de Perú, ADR 0012).
_FLETE_FIN = FleteDetalle(
    flete_id="F-101", viaje_id="T07-V11", vehiculo="T07", conductor="Hugo Montalvo",
    cliente="Aceros del Norte S.A.", ruc_cliente="20481234565", carga="Perfiles de acero", toneladas=24.4,
    corredor="LIM-AQP", sentido="vuelta", origen="AQP", destino="LIM", salida=utc(2020, 4, 13, 14, 18),
    llegada=utc(2020, 4, 14, 6, 2), estado="finalizado", gre_remitente="T001-00031415",
    gre_transportista="V001-00000101", tarifa_pen=4190.0, igv_pen=754.2, total_pen=4944.2, detraccion_pen=197.77,
    km=1009.4, litros=479.6, l_100km=47.51, combustible_pen=2062.28, margen_pen=2127.72,
)
_FLETE_CURSO = _FLETE_FIN.model_copy(update=dict(
    flete_id="F-102", viaje_id="T03-V12", vehiculo="T03", conductor="Marcos Quispe", sentido="ida", origen="LIM",
    destino="AQP", salida=utc(2020, 4, 14, 1, 30), llegada=None, estado="en_curso", gre_transportista="V001-00000102",
    km=None, litros=None, l_100km=None, combustible_pen=None, margen_pen=None,
))
_AGG = dict(fletes=1, toneladas=24.4, ingresos_pen=4190.0, combustible_pen=2062.28, margen_pen=2127.72,
            margen_pct=50.8, l_100km=47.51)
FREIGHT_BOARD = FreightBoard(
    resumen=ResumenFletes(clave="total", en_curso=1, programados=0, igv_pen=754.2, detraccion_pen=197.77,
                          litros=479.6, km=1009.4, **_AGG),
    por_corredor=[AgregadoFletes(clave="LIM-AQP", **_AGG)],
    por_cliente=[AgregadoFletes(clave="Aceros del Norte S.A.", **_AGG)],
    por_vehiculo=[AgregadoFletes(clave="T07", **_AGG)],
    por_dia=[AgregadoFletes(clave="2020-04-14", **_AGG)],
    fletes=[_FLETE_FIN, _FLETE_CURSO],
)

_DIA_13 = MetricasPeriodo(
    clave="2020-04-13", viajes_finalizados=1, km=812.4, litros=301.5, l_100km=37.11, tramos=118,
    tramos_con_linea_base=112, tramos_sobreconsumo=3, litros_linea_base=284.0, exceso_l=11.2, vs_pares_pct=4.1,
    horas_en_movimiento=13.6, ralenti_h=0.42, ingresos_pen=3850.0, combustible_pen=1296.45, margen_pen=2553.55,
)
_DIA_14 = _DIA_13.model_copy(update=dict(
    clave="2020-04-14", viajes_finalizados=0, km=640.2, litros=305.8, l_100km=47.77, tramos=93,
    tramos_con_linea_base=90, tramos_sobreconsumo=21, litros_linea_base=232.6, exceso_l=66.1, vs_pares_pct=28.4,
    horas_en_movimiento=10.9, ralenti_h=0.35, ingresos_pen=0.0, combustible_pen=0.0, margen_pen=0.0,
))
VEHICLE_METRICS = VehicleMetrics(
    alias="T07", agrupar_por="dia", desde="2020-04-13", hasta="2020-04-14",
    resumen=_DIA_13.model_copy(update=dict(
        clave="total", km=1452.6, litros=607.3, l_100km=41.81, tramos=211, tramos_con_linea_base=202,
        tramos_sobreconsumo=24, litros_linea_base=516.6, exceso_l=77.3, vs_pares_pct=15.0,
        horas_en_movimiento=24.5, ralenti_h=0.77,
    )),
    filas=[_DIA_13, _DIA_14],
)


# Lima–Arequipa real, simplificado a ~150 m para que el contrato sea liviano; T03, T07 y T04 están sobre él.
CORRIDORS = CorridorList(corredores=[
    Corredor(**json.loads((Path(__file__).with_name("examples_corredor.json")).read_text(encoding="utf-8")))
])
