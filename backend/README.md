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
