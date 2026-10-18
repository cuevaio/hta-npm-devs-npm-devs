import json

from fleetdata.anonymize import anonymize
from fleetdata.extract import iter_rows


def test_la_salida_usa_alias_y_no_contiene_datos_personales(fake_fleet):
    amap = fake_fleet["alias_map"]
    hashes = {h: a for h, a in amap.items() if a in ("T01", "T02")}
    out = list(anonymize(iter_rows(fake_fleet["archive"], hashes), hashes))
    assert out and {r["alias"] for r in out} == {"T01", "T02"}
    blob = json.dumps(out, ensure_ascii=False)
    for v in fake_fleet["vehicles"]:
        assert v["plate"] not in blob and v["imei"] not in blob and v["hash"] not in blob
    assert "哈尔滨" not in blob and "某某路" not in blob
    assert all(set(r) == {"alias", "ems_time", "signals", "lat", "lon"} for r in out)
    assert all(h not in blob for h in amap)  # la tabla alias<->hash no sale
