"""Con la base saturada las lecturas fallan rápido con 503 en vez de quedarse colgadas.

Producción (2026-10-18): sin timeouts, cada poll del dashboard dejaba una consulta corriendo minutos en
Cloud SQL; se acumularon hasta llenar la única instancia de Cloud Run y todo respondió 429.
"""

import time

import psycopg
from fastapi.testclient import TestClient

from app.main import create_app


def test_read_returns_503_when_query_exceeds_statement_timeout(loaded, clock):
    api = TestClient(create_app(loaded, api_key="secreta", clock=clock, statement_timeout_ms=300))
    with psycopg.connect(loaded) as blocker:
        blocker.execute("LOCK TABLE replay_state IN ACCESS EXCLUSIVE MODE")  # la lectura espera este lock

        start = time.monotonic()
        response = api.get("/v1/fleet")
        elapsed = time.monotonic() - start

        blocker.rollback()

    assert response.status_code == 503
    assert "ocupada" in response.json()["detail"]
    assert elapsed < 5


def test_reads_work_again_after_the_database_frees_up(loaded, clock):
    api = TestClient(create_app(loaded, api_key="secreta", clock=clock, statement_timeout_ms=300))
    with psycopg.connect(loaded) as blocker:
        blocker.execute("LOCK TABLE replay_state IN ACCESS EXCLUSIVE MODE")
        assert api.get("/v1/replay").status_code == 503
        blocker.rollback()

    assert api.get("/v1/replay").status_code == 200
    assert api.get("/v1/fleet").status_code == 200
