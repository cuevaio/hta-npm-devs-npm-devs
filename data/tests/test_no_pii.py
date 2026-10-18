"""Falla si la salida (fixtures) contiene matrículas, IMEI o hashes de camión."""
from pathlib import Path

from fleetdata.pii import scan_dir, scan_text

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def test_fixtures_sin_matriculas_imei_ni_hashes():
    assert scan_dir(FIXTURES) == []


def test_el_detector_si_falla_con_datos_sucios(tmp_path):
    (tmp_path / "sucio.csv").write_text("alias,x\nT03,黑A00001\n", encoding="utf-8")
    (tmp_path / "imei.csv").write_text("a,b\n1,123456789012345\n")
    (tmp_path / "hash.csv").write_text("a\n00000000000000000000000000000ABC\n")
    (tmp_path / "sha.json").write_text('{"h": "' + "ab" * 20 + '"}')
    hits = {(p.name, w) for p, w in scan_dir(tmp_path)}
    assert {("sucio.csv", "matrícula"), ("imei.csv", "imei"), ("hash.csv", "hash"), ("sha.json", "hash")} <= hits


def test_valores_normales_no_son_falsos_positivos():
    assert scan_text("T03,2020-04-03T17:53:10Z,45.994545,126.615074,79.0,700.0,3.5,30010.5,1234.0,true,fead_observed") == []
