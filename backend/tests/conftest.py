import pytest
from fastapi.testclient import TestClient
from testcontainers.community.postgres import PostgresContainer

from app.main import create_app

POSTGIS_IMAGE = "postgis/postgis:16-3.4"


@pytest.fixture(scope="session")
def database_url():
    with PostgresContainer(POSTGIS_IMAGE, driver=None) as pg:
        url = pg.get_connection_url()
        import psycopg

        with psycopg.connect(url, autocommit=True) as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        yield url


@pytest.fixture
def client(database_url):
    return TestClient(create_app(database_url))
