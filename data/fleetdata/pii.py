"""Detector de datos personales en salidas de texto: matrículas chinas, IMEI y hashes de camión."""
from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

PROVINCES = "京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼"
PATTERNS = {
    "matrícula": re.compile(rf"[{PROVINCES}][A-Z][A-Z0-9]{{5,6}}"),
    "imei": re.compile(r"(?<![\d.])\d{15}(?![\d])"),
    "hash": re.compile(r"(?<![0-9a-fA-F])(?:[0-9a-fA-F]{64}|[0-9a-fA-F]{40}|[0-9a-fA-F]{32})(?![0-9a-fA-F])"),
    "texto chino": re.compile(r"[一-鿿]"),
}
TEXT_SUFFIXES = {".csv", ".json", ".txt", ".md", ".tsv", ".jsonl"}


def scan_text(text: str, forbidden: Iterable[str] = ()) -> list[str]:
    found = [name for name, rx in PATTERNS.items() if rx.search(text)]
    found += ["valor privado" for v in forbidden if v and v in text]
    return found


def scan_dir(root: Path, forbidden: Iterable[str] = ()) -> list[tuple[Path, str]]:
    forbidden = list(forbidden)
    hits = []
    for p in sorted(Path(root).rglob("*")):
        if p.is_file() and p.suffix in TEXT_SUFFIXES:
            for what in scan_text(p.read_text(encoding="utf-8", errors="replace"), forbidden):
                hits.append((p, what))
    return hits
