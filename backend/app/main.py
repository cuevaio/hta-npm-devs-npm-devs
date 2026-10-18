import asyncio
import hmac
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Annotated, Callable

import psycopg
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from . import examples as ex
from . import freights as freights_mod
from . import fuel as fuel_mod
from . import reads
from .db import migrate
from .replay import Clock, ReplayEngine, system_clock
from .schemas import (
    AlertList, Bottlenecks, ControlReplayRequest, Envelope, ErrorBody, FleetOverview, FreightBoard, FuelAnalysis,
    Provenance, ReplayState, TimeRange, TripStatus, VehicleStatus,
)

# Previews y producción del dashboard y la landing en Vercel (ADR 0011).
VERCEL_ORIGIN_REGEX = r"^https://[a-z0-9-]+\.vercel\.app$"

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False, description="Clave de la Domain API (variable API_KEY)")


def require_api_key(request: Request, key: str | None = Security(api_key_header)) -> None:
    expected: str | None = request.app.state.api_key
    if not expected:  # nunca quedan abiertas si falta la configuración
        raise HTTPException(status_code=503, detail="API_KEY no está configurada en el servidor")
    if key is None or not hmac.compare_digest(key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="X-API-Key ausente o incorrecta")


def envelope(data, provenance: list[Provenance], time_range: TimeRange, updated_at: datetime = ex.UPDATED_AT) -> dict:
    return Envelope(
        data=data, provenance=provenance, time_range=time_range, updated_at=updated_at, is_replay=True
    ).model_dump(mode="json", by_alias=True)


def example_response(model, body: dict) -> dict:
    return {
        200: {"model": model, "content": {"application/json": {"example": body}}},
    }


FREIGHT_PROVENANCE = [Provenance.synthetic_demo, Provenance.model_inferred]

NOT_FOUND = {404: {"model": ErrorBody, "description": "Alias o viaje desconocido"}}
AUTH_ERRORS = {
    401: {"model": ErrorBody, "description": "X-API-Key ausente o incorrecta"},
    503: {"model": ErrorBody, "description": "API_KEY no configurada en el servidor"},
}


def _trip_id(trip_id: str) -> str:
    if trip_id not in ex.TRIPS:
        raise HTTPException(status_code=404, detail=f"Viaje desconocido: {trip_id}")
    return trip_id


def create_app(
    database_url: str | None = None,
    api_key: str | None = None,
    cors_origins: list[str] | None = None,
    clock: Clock = system_clock,
    tick_interval: float = 1.0,
) -> FastAPI:
    database_url = database_url or os.environ.get("DATABASE_URL")
    api_key = api_key or os.environ.get("API_KEY") or None
    if cors_origins is None:
        cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "").split(",") if o.strip()]

    engine = ReplayEngine(database_url, clock) if database_url else None

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        task = None
        if engine:
            await asyncio.to_thread(migrate, database_url)  # el replay arranca en pausa
            task = asyncio.create_task(engine.run(tick_interval))
        yield
        if task:
            task.cancel()

    app = FastAPI(
        lifespan=lifespan,
        title="Fleet Intelligence · Domain API",
        version="0.1.0",
        description=(
            "Contrato de la Domain API con datos de ejemplo. Toda respuesta va en un sobre con "
            "procedencia, rango de tiempo (hora del evento, UTC) y hora de última actualización. "
            "Las rutas `/v1/tools/*` (MCP, Zavu y control del replay) exigen `X-API-Key`; "
            "las lecturas `/v1/*` del dashboard son públicas."
        ),
    )
    app.state.api_key = api_key
    app.state.database_url = database_url
    app.state.replay_engine = engine

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=VERCEL_ORIGIN_REGEX,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["X-API-Key", "Content-Type"],
    )

    @app.get("/health", include_in_schema=False)
    def health() -> dict:
        if not database_url:
            raise HTTPException(status_code=503, detail="database unavailable: DATABASE_URL not set")
        try:
            with psycopg.connect(database_url, connect_timeout=5) as conn:
                postgis = conn.execute("SELECT postgis_version()").fetchone()[0]
        except psycopg.Error as exc:
            raise HTTPException(status_code=503, detail=f"database unavailable: {exc.__class__.__name__}")
        return {"status": "ok", "postgis": postgis}

    # --- Handlers compartidos por las rutas públicas y las de tools ---

    def need_engine() -> ReplayEngine:
        if engine is None:
            raise HTTPException(status_code=503, detail="database unavailable: DATABASE_URL not set")
        return engine

    def telemetry() -> list[Provenance]:
        """Procedencia de la telemetría cargada: synthetic_demo con la flota de Perú (ADR 0012)."""
        return [Provenance(p) for p in reads.telemetry_provenance(database_url)] or [Provenance.synthetic_demo]

    def real() -> list[Provenance]:
        return list(dict.fromkeys([*telemetry(), Provenance.synthetic_demo]))

    def fleet() -> dict:
        need_engine()
        data, desde, hasta, updated = reads.fleet_overview(database_url)
        return envelope(data, real(), TimeRange(from_=desde, to=hasta), updated)

    def vehicle(alias: str) -> dict:
        need_engine()
        found = reads.vehicle_status(database_url, alias)
        if found is None:
            raise HTTPException(status_code=404, detail=f"Vehículo desconocido: {alias}")
        data, desde, hasta, updated = found
        return envelope(data, real(), TimeRange(from_=desde, to=hasta), updated)

    def trip(trip_id: str) -> dict:
        need_engine()
        found = fuel_mod.trip_status(database_url, trip_id)
        if found is None:
            raise HTTPException(status_code=404, detail=f"Viaje desconocido: {trip_id}")
        data, desde, hasta, updated = found
        return envelope(data, real(), TimeRange(from_=desde, to=hasta), updated)

    def fuel(trip_id: str) -> dict:
        need_engine()
        found = fuel_mod.fuel_analysis(database_url, trip_id)
        if found is None:
            raise HTTPException(status_code=404, detail=f"Viaje desconocido: {trip_id}")
        data, desde, hasta, updated = found
        return envelope(data, [*real(), Provenance.model_inferred], TimeRange(from_=desde, to=hasta), updated)

    def bottlenecks(trip_id: str) -> dict:
        t = ex.TRIPS[_trip_id(trip_id)]
        return envelope(ex.BOTTLENECKS[trip_id], ex.PROVENANCE_ALERTS, TimeRange(from_=t.inicio, to=ex.NOW))

    def alerts() -> dict:
        return envelope(AlertList(alertas=[ex.ALERTA]), ex.PROVENANCE_ALERTS, TimeRange(from_=ex.T0, to=ex.NOW))

    def replay_state() -> dict:
        r, updated = need_engine().state()
        return envelope(r, telemetry(), TimeRange(from_=r.inicio, to=r.fin), updated)

    def freights() -> dict:
        need_engine()
        data, desde, hasta, updated = freights_mod.freight_board(database_url)
        return envelope(data, FREIGHT_PROVENANCE, TimeRange(from_=desde, to=hasta), updated)

    # Ejemplos del contrato (OpenAPI y mock): no dependen de la base.
    v_ex = ex.VEHICLE_STATUS["T03"]
    ex_fleet = envelope(ex.FLEET, ex.PROVENANCE, TimeRange(from_=ex.T0, to=ex.NOW))
    ex_vehicle = envelope(v_ex, ex.PROVENANCE, TimeRange(from_=ex.T0, to=v_ex.hora_evento))
    ex_trip_t = ex.TRIPS["V-001"]
    ex_trip = envelope(ex_trip_t, ex.PROVENANCE, TimeRange(from_=ex_trip_t.inicio, to=ex.NOW))
    ex_fuel = envelope(ex.FUEL["V-001"], ex.PROVENANCE, TimeRange(from_=ex_trip_t.inicio, to=ex.NOW))
    ex_bottlenecks = bottlenecks("V-001")
    ex_alerts = alerts()
    r_ex = ex.INITIAL_REPLAY
    ex_replay = envelope(r_ex, [Provenance.synthetic_demo], TimeRange(from_=r_ex.inicio, to=r_ex.fin), ex.UPDATED_AT)
    ex_freights = envelope(ex.FREIGHT_BOARD, FREIGHT_PROVENANCE, TimeRange(from_=ex.T0, to=ex.NOW))

    public = APIRouter(prefix="/v1", tags=["dashboard (público)"])
    tools = APIRouter(prefix="/v1/tools", tags=["tools (X-API-Key)"], dependencies=[Depends(require_api_key)])

    Alias = Annotated[str, Query(description="Alias del vehículo, p. ej. T03")]
    TripId = Annotated[str, Query(description="Identificador del viaje, p. ej. V-001")]

    def add(router: APIRouter, path: str, op: str, fn: Callable, model, example: dict, summary: str, errors: dict):
        router.add_api_route(
            path, fn, methods=["GET"], operation_id=op, summary=summary,
            response_model=Envelope[model], responses={**example_response(Envelope[model], example), **errors},
        )

    # Públicas (lecturas del dashboard)
    add(public, "/fleet", "read_fleet", lambda: fleet(), FleetOverview, ex_fleet, "Vista general de la flota", {})
    add(public, "/vehicles/{alias}", "read_vehicle", lambda alias: vehicle(alias), VehicleStatus, ex_vehicle, "Estado de un vehículo", NOT_FOUND)
    add(public, "/trips/{trip_id}", "read_trip", lambda trip_id: trip(trip_id), TripStatus, ex_trip, "Estado de un viaje", NOT_FOUND)
    add(public, "/trips/{trip_id}/fuel", "read_trip_fuel", lambda trip_id: fuel(trip_id), FuelAnalysis, ex_fuel, "Análisis de combustible de un viaje", NOT_FOUND)
    add(public, "/trips/{trip_id}/bottlenecks", "read_trip_bottlenecks", lambda trip_id: bottlenecks(trip_id), Bottlenecks, ex_bottlenecks, "Cuellos de botella de un viaje", NOT_FOUND)
    add(public, "/alerts", "read_alerts", lambda: alerts(), AlertList, ex_alerts, "Alertas enviadas al gestor de flota", {})
    add(public, "/freights", "read_freights", lambda: freights(), FreightBoard, ex_freights, "Tablero de fletes: ingresos, combustible y margen", {})
    add(public, "/replay", "read_replay", lambda: replay_state(), ReplayState, ex_replay, "Estado del replay", {})

    # Tools (MCP, Zavu): operationId = nombre de la tool
    def tool_vehicle(alias: Alias): return vehicle(alias)
    def tool_trip(trip_id: TripId): return trip(trip_id)
    def tool_fuel(trip_id: TripId): return fuel(trip_id)
    def tool_bottlenecks(trip_id: TripId): return bottlenecks(trip_id)

    add(tools, "/get_fleet_overview", "get_fleet_overview", lambda: fleet(), FleetOverview, ex_fleet, "Tool get_fleet_overview", AUTH_ERRORS)
    add(tools, "/get_vehicle_status", "get_vehicle_status", tool_vehicle, VehicleStatus, ex_vehicle, "Tool get_vehicle_status", {**NOT_FOUND, **AUTH_ERRORS})
    add(tools, "/get_trip_status", "get_trip_status", tool_trip, TripStatus, ex_trip, "Tool get_trip_status", {**NOT_FOUND, **AUTH_ERRORS})
    add(tools, "/get_fuel_analysis", "get_fuel_analysis", tool_fuel, FuelAnalysis, ex_fuel, "Tool get_fuel_analysis (desglose por tramo y sentido)", {**NOT_FOUND, **AUTH_ERRORS})
    add(tools, "/get_operational_bottlenecks", "get_operational_bottlenecks", tool_bottlenecks, Bottlenecks, ex_bottlenecks, "Tool get_operational_bottlenecks", {**NOT_FOUND, **AUTH_ERRORS})
    add(tools, "/get_alerts", "get_alerts", lambda: alerts(), AlertList, ex_alerts, "Tool get_alerts", AUTH_ERRORS)

    def control_replay(body: ControlReplayRequest) -> dict:
        eng = need_engine()
        if body.action == "play":
            eng.play()
        elif body.action == "pause":
            eng.pause()
        elif body.action == "set_speed":
            if body.speed is None:
                raise HTTPException(status_code=422, detail="set_speed requiere speed")
            eng.set_speed(body.speed)
        else:
            if body.to_event_time is None:
                raise HTTPException(status_code=422, detail="seek requiere to_event_time")
            r, _ = eng.state()
            if not r.inicio <= body.to_event_time <= r.fin:
                raise HTTPException(status_code=422, detail="to_event_time fuera del rango del replay")
            eng.seek(body.to_event_time)
        return replay_state()

    tools.add_api_route(
        "/control_replay", control_replay, methods=["POST"], operation_id="control_replay",
        summary="Tool control_replay (escritura)", response_model=Envelope[ReplayState],
        responses={**example_response(Envelope[ReplayState], ex_replay), **AUTH_ERRORS},
    )

    app.include_router(public)
    app.include_router(tools)
    return app
