import shutil
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer

from app.db import migrate
from app.main import create_app
from scripts.load_demo_data import load
from tests.helpers import FakeClock, REPLAY_START

POSTGIS_IMAGE = "postgis/postgis:16-3.4"
REPO = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def database_url():
    with PostgresContainer(POSTGIS_IMAGE, driver=None) as pg:
        url = pg.get_connection_url()
        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        migrate(url)
        yield url


@pytest.fixture
def source_dir(tmp_path):
    """Salida de pipeline en miniatura: enlaces al fixture de data/ (sin copiarlo) y a los de pruebas."""
    for name in ("telemetry.csv", "drivers.csv", "driver_reports.csv"):
        (tmp_path / name).symlink_to(REPO / "data" / "fixtures" / name)
    for name in ("trips.csv", "freights.csv", "passes_demo.csv", "baseline.csv"):
        shutil.copy(FIXTURES / name, tmp_path / name)
    return tmp_path


@pytest.fixture
def loaded(database_url, source_dir):
    """Base con el fixture cargado y el replay en pausa al inicio."""
    load(source_dir, database_url, REPLAY_START)
    return database_url


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def app(loaded, clock):
    return create_app(loaded, api_key="secreta", clock=clock)


@pytest.fixture
def api(app):
    return TestClient(app)


@pytest.fixture
def client(database_url):
    return TestClient(create_app(database_url))
