"""Datos de ejemplo coherentes (sintéticos) para el contrato. Sin base de datos."""

from datetime import UTC, datetime

from .schemas import (
    Alerta, Anomalia, Bottlenecks, CuelloDeBotella, Flete, FleetOverview, FuelAnalysis, LineaBase,
    Pasada, Posicion, Provenance, ReplayState, ReporteConductor, TimeRange, Tramo, TripStatus,
    VehicleStatus, VehiculoResumen,
)


def utc(*args: int) -> datetime:
    return datetime(*args, tzinfo=UTC)


UPDATED_AT = utc(2020, 4, 14, 3, 30)
REPLAY_START = utc(2020, 4, 13, 0, 0)
REPLAY_END = utc(2020, 4, 19, 23, 59)
CORREDOR = "Harbin-Guangzhou"

PROVENANCE = [Provenance.fead_observed, Provenance.synthetic_demo, Provenance.model_inferred]
PROVENANCE_ALERTS = [*PROVENANCE, Provenance.human_reported]

T0 = utc(2020, 4, 14, 0, 0)
NOW = utc(2020, 4, 14, 3, 30)

H3 = ["86309a0f7ffffff", "86309a0efffffff", "86309a0c7ffffff", "86309a0dfffffff"]


def _t(i: int, sentido="ida") -> Tramo:
    return Tramo(h3=H3[i], sentido=sentido)


def _pos(lat: float, lon: float) -> Posicion:
    return Posicion(lat=lat, lon=lon)


VEHICLES = {
    "T03": VehiculoResumen(alias="T03", estado="en_viaje", viaje_id="V-001", velocidad_kmh=72.5, posicion=_pos(28.19, 113.02), hora_evento=NOW),
    "T07": VehiculoResumen(alias="T07", estado="en_viaje", viaje_id="V-002", velocidad_kmh=64.0, posicion=_pos(30.57, 114.30), hora_evento=NOW),
    "T28": VehiculoResumen(alias="T28", estado="detenido", velocidad_kmh=0.0, posicion=_pos(45.75, 126.63), hora_evento=NOW),
    "T04": VehiculoResumen(alias="T04", estado="ralenti", velocidad_kmh=0.0, posicion=_pos(34.75, 113.62), hora_evento=NOW),
    "T22": VehiculoResumen(alias="T22", estado="detenido", velocidad_kmh=0.0, posicion=_pos(23.13, 113.26), hora_evento=NOW),
    "T09": VehiculoResumen(alias="T09", estado="detenido", velocidad_kmh=0.0, posicion=_pos(45.80, 126.53), hora_evento=NOW),
}

REPORTE = ReporteConductor(
    texto="Hay obras en el paso de Nanling, estamos parados hace media hora",
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
        viaje_id="V-001", vehiculo_alias="T03", conductor="Wang Lei (sintético)",
        flete=Flete(id="F-101", carga="Autopartes", cliente="Cliente Demo S.A.", origen="Harbin", destino="Guangzhou"),
        corredor=CORREDOR, sentido="ida", estado="en_curso", inicio=utc(2020, 4, 13, 18, 0), distancia_km=1840.5, progreso_pct=53.2,
    ),
    "V-002": TripStatus(
        viaje_id="V-002", vehiculo_alias="T07", conductor="Li Na (sintético)",
        flete=Flete(id="F-102", carga="Electrodomésticos", cliente="Cliente Demo S.A.", origen="Harbin", destino="Guangzhou"),
        corredor=CORREDOR, sentido="ida", estado="en_curso", inicio=utc(2020, 4, 13, 20, 0), distancia_km=1320.0, progreso_pct=38.3,
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
                            impacto_min=42.0, explicada=False, posicion=_pos(28.0, 113.1)),
            CuelloDeBotella(tipo="ralenti_prolongado", inicio=utc(2020, 4, 14, 2, 20), fin=utc(2020, 4, 14, 2, 41), duracion_min=21.0,
                            impacto_min=20.0, explicada=True, reporte_conductor=REPORTE, posicion=_pos(28.19, 113.02)),
        ],
    ),
    "V-002": Bottlenecks(
        viaje_id="V-002", tiempo_perdido_min=0.0,
        cuellos_de_botella=[
            CuelloDeBotella(tipo="parada_explicada", inicio=utc(2020, 4, 14, 0, 30), fin=utc(2020, 4, 14, 0, 55), duracion_min=25.0,
                            impacto_min=0.0, explicada=True, posicion=_pos(30.5, 114.2)),
        ],
    ),
}

VEHICLE_STATUS = {
    "T03": VehicleStatus(**VEHICLES["T03"].model_dump(), corredor=CORREDOR, sentido="ida", conductor="Wang Lei (sintético)", ultima_alerta_id="AL-001"),
    "T07": VehicleStatus(**VEHICLES["T07"].model_dump(), corredor=CORREDOR, sentido="ida", conductor="Li Na (sintético)"),
}
for _a, _v in VEHICLES.items():
    VEHICLE_STATUS.setdefault(_a, VehicleStatus(**_v.model_dump()))

FLEET = FleetOverview(total_vehiculos=len(VEHICLES), viajes_en_curso=len(TRIPS), alertas_abiertas=1, vehiculos=list(VEHICLES.values()))

INITIAL_REPLAY = ReplayState(estado="paused", velocidad=1.0, hora_replay=REPLAY_START, inicio=REPLAY_START, fin=REPLAY_END)


def range_from(*times: datetime) -> TimeRange:
    return TimeRange(from_=min(times), to=max(times))
