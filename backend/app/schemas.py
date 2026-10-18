"""Contrato de la Domain API: modelos con el vocabulario de CONTEXT.md.

Las claves de `data` usan el glosario (viaje, flete, corredor, sentido, tramo,
pasada, línea base...) sin tildes. El sobre (`Envelope`) es común a todas las
respuestas y declara procedencia, rango de tiempo y última actualización.
"""

from enum import StrEnum
from typing import Generic, Literal, TypeVar

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field


class Provenance(StrEnum):
    """Procedencia de un dato (CONTEXT.md)."""

    fead_observed = "fead_observed"
    synthetic_demo = "synthetic_demo"
    human_reported = "human_reported"
    external_enrichment = "external_enrichment"
    model_inferred = "model_inferred"


class TimeRange(BaseModel):
    """Rango de tiempo de los datos, en hora del evento (UTC)."""

    model_config = ConfigDict(populate_by_name=True)

    from_: AwareDatetime = Field(alias="from", description="Inicio (hora del evento, UTC)")
    to: AwareDatetime = Field(description="Fin (hora del evento, UTC)")


T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    data: T
    provenance: list[Provenance] = Field(min_length=1, description="Procedencia de los datos de la respuesta")
    time_range: TimeRange
    updated_at: AwareDatetime = Field(description="Hora de última actualización (UTC)")
    is_replay: bool = Field(description="Siempre true en la demo: los datos son un replay, nunca tiempo real")


class ErrorBody(BaseModel):
    detail: str


Sentido = Literal["ida", "vuelta"]


class Posicion(BaseModel):
    lat: float
    lon: float


class ReporteConductor(BaseModel):
    """Mensaje de WhatsApp de un conductor, con su texto original."""

    texto: str
    recibido_en: AwareDatetime = Field(description="Hora de ingesta del reporte (UTC)")
    procedencia: Provenance = Provenance.human_reported


class Flete(BaseModel):
    id: str = Field(description="Identificador sintético, p. ej. F-101")
    carga: str
    cliente: str
    origen: str
    destino: str


class VehiculoResumen(BaseModel):
    alias: str = Field(description="Alias anónimo del vehículo, T01…T28")
    estado: Literal["en_viaje", "detenido", "ralenti"]
    viaje_id: str | None = None
    velocidad_kmh: float
    posicion: Posicion
    hora_evento: AwareDatetime = Field(description="Hora del evento de la última lectura (UTC)")


class FleetOverview(BaseModel):
    total_vehiculos: int
    viajes_en_curso: int
    alertas_abiertas: int
    vehiculos: list[VehiculoResumen]


class VehicleStatus(VehiculoResumen):
    corredor: str | None = None
    sentido: Sentido | None = None
    conductor: str | None = Field(None, description="Nombre sintético del conductor")
    ultima_alerta_id: str | None = None


class TripStatus(BaseModel):
    viaje_id: str
    vehiculo_alias: str
    conductor: str
    flete: Flete
    corredor: str
    sentido: Sentido
    estado: Literal["en_curso", "finalizado"]
    inicio: AwareDatetime
    fin: AwareDatetime | None = None
    distancia_km: float
    progreso_pct: float = Field(ge=0, le=100)


class Tramo(BaseModel):
    """Celda H3 de resolución 6 recorrida en un sentido (ADR 0008)."""

    h3: str
    sentido: Sentido


class LineaBase(BaseModel):
    """Consumo esperado de un tramo según sus pares (ADR 0002, 0009)."""

    mediana_l: float
    p90_l: float
    n_pasadas: int = Field(description="Pasadas de pares con las que se calculó")


class Pasada(BaseModel):
    tramo: Tramo
    consumo_observado_l: float
    linea_base: LineaBase | None = Field(None, description="Nula si el tramo no tiene suficientes pasadas")
    sobreconsumo: bool
    exceso_l: float | None = Field(None, description="Litros sobre la mediana; nulo sin línea base")
    ralenti_min: float


class Anomalia(BaseModel):
    id: str
    viaje_id: str
    vehiculo_alias: str
    tramos: list[Tramo] = Field(description="Tramos seguidos con sobreconsumo")
    exceso_l: float
    evidencia: str
    detectada_en: AwareDatetime


class FuelAnalysis(BaseModel):
    viaje_id: str
    distancia_km: float
    consumo_observado_l: float
    consumo_l_100km: float
    exceso_total_l: float
    pasadas: list[Pasada]
    anomalias: list[Anomalia]


class CuelloDeBotella(BaseModel):
    tipo: Literal["parada_sin_explicar", "ralenti_prolongado", "parada_explicada"]
    inicio: AwareDatetime
    fin: AwareDatetime
    duracion_min: float
    impacto_min: float = Field(description="Tiempo perdido; ordena la lista de mayor a menor")
    explicada: bool = Field(description="Una parada explicada por el conductor sigue visible")
    reporte_conductor: ReporteConductor | None = None
    posicion: Posicion


class Bottlenecks(BaseModel):
    viaje_id: str
    tiempo_perdido_min: float
    cuellos_de_botella: list[CuelloDeBotella]


class Alerta(BaseModel):
    id: str
    anomalia: Anomalia
    enviada_en: AwareDatetime = Field(description="Hora del evento en que se envió al gestor de flota")
    mensaje: str
    reporte_conductor: ReporteConductor | None = None


class AlertList(BaseModel):
    alertas: list[Alerta]


class ReplayState(BaseModel):
    estado: Literal["playing", "paused"]
    velocidad: float = Field(gt=0, description="Multiplicador de velocidad del replay")
    hora_replay: AwareDatetime = Field(description="Posición actual del replay, en hora del evento (UTC)")
    inicio: AwareDatetime
    fin: AwareDatetime


class ControlReplayRequest(BaseModel):
    action: Literal["play", "pause", "seek", "set_speed"]
    speed: float | None = Field(None, gt=0, description="Requerido con set_speed")
    to_event_time: AwareDatetime | None = Field(None, description="Requerido con seek (hora del evento, UTC)")


EstadoFlete = Literal["programado", "en_curso", "finalizado"]


class FleteDetalle(BaseModel):
    """Flete con su capa comercial (soles). Combustible y margen solo cuando el viaje ya terminó en el replay."""

    flete_id: str
    viaje_id: str
    vehiculo: str
    conductor: str | None
    cliente: str
    ruc_cliente: str | None = Field(description="RUC ficticio de la demo")
    carga: str
    toneladas: float | None
    corredor: str
    sentido: Sentido
    origen: str
    destino: str
    salida: AwareDatetime
    llegada: AwareDatetime | None = Field(description="Solo si el viaje ya terminó")
    estado: EstadoFlete
    gre_remitente: str | None
    gre_transportista: str | None
    tarifa_pen: float | None = Field(description="Flete sin IGV")
    igv_pen: float | None
    total_pen: float | None
    detraccion_pen: float | None = Field(description="4 % del total si supera S/ 400")
    km: float | None
    litros: float | None
    l_100km: float | None
    combustible_pen: float | None
    margen_pen: float | None = Field(description="Tarifa sin IGV menos combustible")


class AgregadoFletes(BaseModel):
    """Totales de los fletes finalizados de un grupo (corredor, cliente, vehículo o día)."""

    clave: str
    fletes: int
    toneladas: float
    ingresos_pen: float
    combustible_pen: float
    margen_pen: float
    margen_pct: float | None
    l_100km: float | None


class ResumenFletes(AgregadoFletes):
    en_curso: int
    programados: int
    igv_pen: float
    detraccion_pen: float
    litros: float
    km: float


class FreightBoard(BaseModel):
    resumen: ResumenFletes
    por_corredor: list[AgregadoFletes]
    por_cliente: list[AgregadoFletes]
    por_vehiculo: list[AgregadoFletes]
    por_dia: list[AgregadoFletes] = Field(description="clave = día (YYYY-MM-DD, hora de Lima) de llegada")
    fletes: list[FleteDetalle]
