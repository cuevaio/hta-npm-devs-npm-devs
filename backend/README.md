# backend · Domain API

FastAPI. Única pieza con lógica de negocio y única que toca la base de datos (ADR 0004). Dueño: Juan.

## Correr

```sh
uv sync
DATABASE_URL=postgresql://... uv run uvicorn app.main:create_app --factory --reload
```

## Tests

```sh
uv run pytest
```

Levantan un Postgres 16 + PostGIS en Docker (testcontainers), así que necesitan Docker corriendo. Prueban la API por HTTP, que es el punto de prueba principal del MVP: comportamiento externo, no detalles internos.

## Contrato (OpenAPI)

El contrato vive en `backend/openapi.json`, exportado de la app FastAPI (con datos de ejemplo estáticos; todavía no lee la base). Todas las respuestas van en un sobre:

```json
{ "data": {}, "provenance": ["fead_observed"], "time_range": {"from": "...", "to": "..."}, "updated_at": "...", "is_replay": true }
```

`time_range` es hora del evento (UTC). `provenance` usa los valores del glosario (`fead_observed`, `synthetic_demo`, `human_reported`, `external_enrichment`, `model_inferred`).

| Lectura pública (dashboard) | Tool (exige `X-API-Key`) |
|---|---|
| `GET /v1/fleet` | `GET /v1/tools/get_fleet_overview` |
| `GET /v1/vehicles/{alias}` | `GET /v1/tools/get_vehicle_status?alias=` |
| `GET /v1/trips/{trip_id}` | `GET /v1/tools/get_trip_status?trip_id=` |
| `GET /v1/trips/{trip_id}/fuel` | `GET /v1/tools/get_fuel_analysis?trip_id=` |
| `GET /v1/trips/{trip_id}/bottlenecks` | `GET /v1/tools/get_operational_bottlenecks?trip_id=` |
| `GET /v1/alerts` | `GET /v1/tools/get_alerts` |
| `GET /v1/replay` (estado) | `POST /v1/tools/control_replay` (`action`: play, pause, seek, set_speed; `speed`; `to_event_time`) |

Ids de ejemplo: vehículos `T03`, `T07`, `T28`, `T04`, `T22`, `T09`; viajes `V-001` (con anomalía y alerta) y `V-002`.

### Auth y CORS

- Las rutas `/v1/tools/*` comparan el header `X-API-Key` con la variable `API_KEY` (401 si falta o es incorrecta). Si `API_KEY` no está configurada responden 503: nunca quedan abiertas.
- Las lecturas `/v1/*` son públicas.
- CORS (ADR 0011): `CORS_ORIGINS` (lista separada por comas) más cualquier `https://*.vercel.app` (previews); permite el header `X-API-Key`.

### Regenerar contrato y tipos

```sh
backend/scripts/gen-api.sh
```

Exporta `openapi.json` y genera los tipos con `openapi-typescript` en `mcp/src/api/types.ts`, `zavu/api/types.ts` y `dashboard/src/api/types.ts`. Si cambias rutas o modelos sin regenerar, `tests/test_openapi.py` falla. Versiona la salida.

### Servidor simulado

```sh
backend/scripts/mock-api.sh   # Prism en http://127.0.0.1:4010 (PORT para cambiarlo)
```

Sirve los ejemplos del `openapi.json`; no valida `X-API-Key`.

## Desplegar en GCP

```sh
tools/wizard-gcp.sh
```

Asistente paso a paso (#10): proyecto y facturación, Cloud SQL Postgres 16 + PostGIS, Secret Manager, imagen en Artifact Registry y Cloud Run con una sola instancia (ADR 0005). Es idempotente: volver a correrlo reutiliza lo que existe y redespliega la imagen del commit actual. Los valores locales quedan en `.env.gcp`, ignorado por git.

En Cloud Run, el backend recibe `DATABASE_URL` (conexión por socket a Cloud SQL) y `API_KEY` desde Secret Manager.
