import psycopg

from app.db import MIGRATIONS_DIR, migrate
from scripts.load_demo_data import load

from tests.helpers import REPLAY_START


def test_migrations_are_idempotent_and_recorded(database_url):
    assert migrate(database_url) == []  # ya aplicadas por el fixture

    with psycopg.connect(database_url) as conn:
        versions = [r[0] for r in conn.execute("SELECT version FROM schema_migrations ORDER BY version")]
    assert versions == sorted(p.stem for p in MIGRATIONS_DIR.glob("*.sql"))
    assert versions[0] == "0001_esquema"


def test_load_splits_history_and_source_at_the_replay_start(loaded):
    with psycopg.connect(loaded) as conn:
        history = conn.execute("SELECT count(*), max(event_time), count(replayed_at) FROM telemetry_reading").fetchone()
        source = conn.execute("SELECT count(*), min(event_time) FROM telemetry_source").fetchone()
        state = conn.execute("SELECT estado, hora_replay, inicio, fin FROM replay_state").fetchone()

    assert history[0] > 0 and history[2] == 0 and history[1] <= REPLAY_START
    assert source[0] > 0 and source[1] > REPLAY_START
    assert history[0] + source[0] == 3196
    assert state[0] == "paused" and state[1] == state[2] == REPLAY_START and state[3] > REPLAY_START


def test_load_is_idempotent(loaded, source_dir):
    with psycopg.connect(loaded) as conn:
        first = [conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                 for t in ("telemetry_reading", "telemetry_source", "trips", "freights", "drivers", "vehicles")]

    load(source_dir, loaded, REPLAY_START)

    with psycopg.connect(loaded) as conn:
        second = [conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                  for t in ("telemetry_reading", "telemetry_source", "trips", "freights", "drivers", "vehicles")]
    assert first == second
