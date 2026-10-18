"""Tar sintético minúsculo con el mismo formato que FEAD EMS-2, con matrículas, IMEI y hashes FALSOS."""
from __future__ import annotations

import io
import json
import random
import tarfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

DAY0 = datetime(2020, 4, 1)  # hora local de la fuente (UTC+8)
N_DAYS = 19
A = (40.0, 116.0)  # terminal A
B = (41.2, 116.0)  # terminal B (~133 km al norte)
SPEED = 80.0
PLATES = ["黑A00001", "黑A00002", "粤B00003", "闽D00004", "吉A00005", "辽B00006"]
ADDRESS = "黑龙江省哈尔滨市道里区某某路1号"


def _fake_hash(rng: random.Random) -> str:
    return "".join(rng.choice("0123456789ABCDEF") for _ in range(32))


def _line(vehicle: dict, t: datetime, lat: float, lon: float, speed: float, fuel: float, odo: float, total: float) -> bytes:
    sig = {"x7000": "1100" if speed else "700", "x7001": f"{fuel:.2f}", "x7002": f"{total:.1f}",
           "x7004": f"{speed:.0f}", "x7005": f"{odo:.0f}", "x006C": f"{speed:.1f}"}
    f = [""] * 24
    f[0] = "0000030955107011585694255000"
    f[1] = json.dumps(sig)
    f[5] = t.strftime("%Y-%m-%d %H:%M:%S")
    f[6] = vehicle["imei"]
    f[8] = vehicle["hash"]
    f[11] = vehicle["plate"]
    f[13], f[14] = f"{lat:.6f}", f"{lon:.6f}"
    f[17:21] = ["黑龙江省", "哈尔滨市", "道里区", ADDRESS]
    f[23] = t.strftime("%Y%m%d")
    return ("\t".join(f) + "\n").encode()


def simulate(vehicle: dict, offset_h: float):
    """Genera (hora local, línea) de un vehículo que va y viene entre A y B durante 19 días."""
    t = DAY0 + timedelta(hours=offset_h)
    end = DAY0 + timedelta(days=N_DAYS)
    pos, dest = A, B
    odo, total = 10000.0, 30000.0
    rows = []
    while t < end:
        for _ in range(24):  # estancia de 4 h, una fila cada 10 min
            rows.append((t, pos, 0.0, 0.0, odo, total)); t += timedelta(minutes=10)
        lat0, lat1 = pos[0], dest[0]
        n = int(abs(lat1 - lat0) * 111.19 / SPEED * 360)  # una fila cada 10 s
        for k in range(1, n + 1):
            lat = lat0 + (lat1 - lat0) * k / n
            rows.append((t, (lat, pos[1]), SPEED, vehicle["fuel"], odo, total))
            t += timedelta(seconds=10)
            odo += SPEED / 360; total += vehicle["fuel"] / 360
        pos, dest = dest, pos
    return [(t, _line(vehicle, t, p[0], p[1], s, f, o, tot)) for t, p, s, f, o, tot in rows if t < end]


@pytest.fixture(scope="session")
def fake_fleet(tmp_path_factory):
    rng = random.Random(7)
    vehicles = []
    for i in range(6):
        vehicles.append({"alias": f"T{i + 1:02d}" if i < 5 else "T29", "hash": _fake_hash(rng),
                         "imei": "".join(str(rng.randrange(10)) for _ in range(15)),
                         "plate": PLATES[i], "fuel": 20.0 + 2 * i})
    days: dict[str, list[bytes]] = {}
    for i, v in enumerate(vehicles):
        for t, line in simulate(v, offset_h=i * 0.5):
            days.setdefault(t.strftime("%Y%m%d"), []).append(line)
    root = tmp_path_factory.mktemp("fake")
    archive = root / "ems.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        for day in sorted(days):
            data = b"".join(days[day])
            ti = tarfile.TarInfo(f"./ems_yingche_{day}.txt")
            ti.size = len(data)
            tar.addfile(ti, io.BytesIO(data))
    alias_map = {v["hash"]: v["alias"] for v in vehicles}
    alias_path = root / "alias.json"
    alias_path.write_text(json.dumps(alias_map))
    return {"archive": archive, "alias_map": alias_map, "alias_path": alias_path, "vehicles": vehicles, "root": root}
