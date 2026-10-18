import os

import psycopg
from fastapi import FastAPI, HTTPException


def create_app(database_url: str | None = None) -> FastAPI:
    database_url = database_url or os.environ["DATABASE_URL"]
    app = FastAPI(title="Fleet Intelligence · Domain API")

    @app.get("/health")
    def health() -> dict:
        try:
            with psycopg.connect(database_url, connect_timeout=5) as conn:
                postgis = conn.execute("SELECT postgis_version()").fetchone()[0]
        except psycopg.Error as exc:
            raise HTTPException(status_code=503, detail=f"database unavailable: {exc.__class__.__name__}")
        return {"status": "ok", "postgis": postgis}

    return app
