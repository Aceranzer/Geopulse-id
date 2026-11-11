"""Tahun yang tersedia pada data kejadian banjir.

Diambil dari nama berkas di data/raw (saat dev). Jika folder raw kosong/tidak ada
(mis. server deploy tidak memuat berkas .xls), dibaca dari data/metrics.json.
"""

import json
import re
from pathlib import Path


def tahun_data(raw_dir):
    """Daftar tahun terurut, mis. [2013, ..., 2017, 2019, 2020, 2024]."""
    files = Path(raw_dir).glob("*kejadian-bencana-banjir*.xls")
    tahun = sorted({int(re.search(r"20\d\d", f.name).group()) for f in files})
    if tahun:
        return tahun
    return _dari_metrics(Path(raw_dir).parent / "metrics.json")


def _dari_metrics(metrics_path):
    """Cadangan: parse rentang_tahun di metrics.json ('2013–2017, 2019–2020, 2024')."""
    if not Path(metrics_path).exists():
        return []
    try:
        with open(metrics_path, encoding="utf-8") as f:
            s = json.load(f).get("rentang_tahun", "")
    except (OSError, ValueError):
        return []
    hasil = set()
    for bagian in s.split(","):
        bagian = bagian.strip().replace("–", "-").replace("—", "-")
        if not bagian:
            continue
        if "-" in bagian:
            a, b = bagian.split("-", 1)
            try:
                hasil.update(range(int(a), int(b) + 1))
            except ValueError:
                continue
        else:
            try:
                hasil.add(int(bagian))
            except ValueError:
                continue
    return sorted(hasil)


def rentang_tahun(tahun):
    """[2013..2017, 2019, 2020, 2024] -> '2013–2017, 2019–2020, 2024'."""
    bagian, awal = [], 0
    for i in range(1, len(tahun) + 1):
        if i == len(tahun) or tahun[i] != tahun[i - 1] + 1:
            a, b = tahun[awal], tahun[i - 1]
            bagian.append(str(a) if a == b else f"{a}–{b}")
            awal = i
    return ", ".join(bagian)
