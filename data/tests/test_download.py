import hashlib

import pytest

from fleetdata.download import ChecksumError, ensure_archive, verify_checksum


@pytest.fixture
def served(tmp_path):
    src = tmp_path / "src" / "ems.tar.gz"
    src.parent.mkdir()
    src.write_bytes(b"contenido de prueba")
    return src, hashlib.sha256(src.read_bytes()).hexdigest()


def test_descarga_y_acepta_el_checksum_correcto(tmp_path, served):
    src, sha = served
    dest = tmp_path / "dl" / "ems.tar.gz"
    assert ensure_archive(dest, url=src.as_uri(), expected_sha256=sha) == dest
    assert dest.read_bytes() == src.read_bytes()


def test_aborta_y_borra_si_el_checksum_no_coincide(tmp_path, served):
    src, _ = served
    dest = tmp_path / "dl" / "ems.tar.gz"
    with pytest.raises(ChecksumError, match="no coincide"):
        ensure_archive(dest, url=src.as_uri(), expected_sha256="0" * 64)
    assert not dest.exists()


def test_reutiliza_el_archivo_existente_y_lo_verifica(tmp_path, served):
    src, sha = served
    ensure_archive(src, url="file:///no-existe", expected_sha256=sha)
    with pytest.raises(ChecksumError):
        verify_checksum(src, "f" * 64)
