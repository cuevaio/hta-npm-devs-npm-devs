from pathlib import Path

import polars as pl

from fleetdata.normalize import NORMALIZED_COLUMNS

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
MAX_BYTES = 1_000_000
MAX_ROWS = 5_000


def test_fixture_versionado_existe_y_cumple_el_esquema_normalizado():
    df = pl.read_csv(FIXTURES / "telemetry.csv")
    assert tuple(df.columns) == NORMALIZED_COLUMNS
    assert set(df["alias"]) <= {"T03", "T07"} and len(df) > 100
    assert df["provenance"].unique().to_list() == ["synthetic_demo"]  # ADR 0012
    assert df["event_time"].str.ends_with("Z").all()
    assert df["alt_m"].null_count() == 0 and df["alt_m"].min() >= 0  # altitud SRTM de la ruta


def test_fixture_es_chico():
    files = list(FIXTURES.glob("*"))
    assert sum(f.stat().st_size for f in files) < MAX_BYTES
    assert len(pl.read_csv(FIXTURES / "telemetry.csv")) <= MAX_ROWS


def test_fixture_incluye_linea_base_y_logistica_sintetica():
    assert pl.read_csv(FIXTURES / "baseline_sample.csv")["n_passes"].min() >= 3
    fr = pl.read_csv(FIXTURES / "freights.csv")
    assert fr["provenance"].unique().to_list() == ["synthetic_demo"]
    assert set(fr["trip_id"]) == set(pl.read_csv(FIXTURES / "trips.csv")["trip_id"])
    assert pl.read_csv(FIXTURES / "driver_reports.csv")["provenance"].unique().to_list() == ["synthetic_demo"]
