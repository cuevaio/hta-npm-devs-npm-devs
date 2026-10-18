"""Conexión y migraciones SQL numeradas (D33)."""

import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row, tuple_row
from psycopg_pool import ConnectionPool

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"
_LOCK_KEY = 1307  # advisory lock: dos arranques no migran a la vez


def migrate(database_url: str, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Aplica en orden las migraciones pendientes, cada una en su transacción. Devuelve las aplicadas."""
    applied: list[str] = []
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (_LOCK_KEY,))
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
            )
            done = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
            for path in sorted(directory.glob("*.sql")):
                if path.stem in done:
                    continue
                with conn.transaction():
                    conn.execute(path.read_text(encoding="utf-8"))
                    conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,))
                applied.append(path.stem)
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_KEY,))
    return applied


# --- Lecturas: pool con timeouts (ver tests/test_db_busy.py) ---
# Sin pool cada lectura abría su conexión, y sin statement_timeout una consulta lenta seguía corriendo en
# Postgres aunque el cliente ya se hubiera ido. Así se saturó Cloud SQL el 2026-10-18.

STATEMENT_TIMEOUT_MS = 10_000
POOL_MAX = 8
POOL_WAIT_S = 10  # si no hay conexión libre en este tiempo, la lectura falla (503) en vez de esperar sin fin

_pools: dict[str, ConnectionPool] = {}
_pools_lock = threading.Lock()


def read_url(database_url: str, statement_timeout_ms: int = STATEMENT_TIMEOUT_MS) -> str:
    """URL de las lecturas: corta toda consulta que pase de `statement_timeout_ms`."""
    return make_conninfo(database_url, connect_timeout=5, options=f"-c statement_timeout={statement_timeout_ms}")


def _pool(url: str) -> ConnectionPool:
    with _pools_lock:
        pool = _pools.get(url)
        if pool is None:
            pool = _pools[url] = ConnectionPool(url, min_size=1, max_size=POOL_MAX, timeout=POOL_WAIT_S, open=True)
        return pool


@contextmanager
def connect(url: str, dict_rows: bool = False) -> Iterator[psycopg.Connection]:
    """Conexión del pool de `url`; hace commit al salir sin error y rollback si hubo excepción."""
    with _pool(url).connection() as conn:
        conn.row_factory = dict_row if dict_rows else tuple_row
        yield conn


def close_pools() -> None:
    with _pools_lock:
        for pool in _pools.values():
            pool.close()
        _pools.clear()
