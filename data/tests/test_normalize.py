import math

from fleetdata.anonymize import anonymize
from fleetdata.extract import iter_rows
from fleetdata.normalize import NORMALIZED_COLUMNS, Telemetry, normalize_row

ROW = {"alias": "T03", "ems_time": "2020-04-04 01:53:10", "lat": "45.994545", "lon": "126.615074",
       "signals": {"x7000": "700", "x7001": "3.50", "x7002": "30010.5", "x7004": "79", "x7005": "1234", "x006C": "78.0"}}


def test_unidades_corregidas_del_perfil():
    epoch, lat, lon, speed, rpm, rate, total, odo, on = normalize_row(ROW)
    assert (rpm, rate, total, speed, odo) == (700.0, 3.5, 30010.5, 79.0, 1234.0)  # x7000 rpm, x7001 L/h, x7002 L, x7004 km/h, x7005 km
    assert (lat, lon) == (45.994545, 126.615074) and on is True


def test_hora_del_evento_en_utc_a_partir_de_hora_local_utc8():
    epoch = normalize_row(ROW)[0]
    from datetime import datetime, timezone
    assert datetime.fromtimestamp(epoch, tz=timezone.utc) == datetime(2020, 4, 3, 17, 53, 10, tzinfo=timezone.utc)


def test_nulos_y_motor_apagado():
    row = {**ROW, "lat": "NULL", "signals": {"x7000": "0"}}
    t = normalize_row(row)
    assert math.isnan(t[1]) and math.isnan(t[5]) and t[8] is False


def test_esquema_procedencia_y_orden(fake_fleet):
    hashes = {h: a for h, a in fake_fleet["alias_map"].items() if a == "T01"}
    buf = Telemetry()
    for r in anonymize(iter_rows(fake_fleet["archive"], hashes), hashes):
        buf.append(normalize_row(r))
    df = buf.to_frame("T01")
    assert tuple(df.columns) == NORMALIZED_COLUMNS
    assert df["provenance"].unique().to_list() == ["fead_observed"]
    assert df["event_time"].dtype.time_zone == "UTC"
    assert df["event_time"].is_sorted() and df["event_time"].is_unique().all()
