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

## Desplegar en GCP

```sh
tools/wizard-gcp.sh
```

Asistente paso a paso (#10): proyecto y facturación, Cloud SQL Postgres 16 + PostGIS, Secret Manager, imagen en Artifact Registry y Cloud Run con una sola instancia (ADR 0005). Es idempotente: volver a correrlo reutiliza lo que existe y redespliega la imagen del commit actual. Los valores locales quedan en `.env.gcp`, ignorado por git.

En Cloud Run, el backend recibe `DATABASE_URL` (conexión por socket a Cloud SQL) y `API_KEY` desde Secret Manager.
