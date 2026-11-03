"""Tahun yang tersedia pada data kejadian banjir (dibaca dari nama berkas di data/raw)."""

import re
from pathlib import Path


def tahun_data(raw_dir):
    """Daftar tahun terurut, mis. [2013, ..., 2017, 2019, 2020, 2024]."""
    files = Path(raw_dir).glob("*kejadian-bencana-banjir*.xls")
    return sorted({int(re.search(r"20\d\d", f.name).group()) for f in files})


def rentang_tahun(tahun):
    """[2013..2017, 2019, 2020, 2024] -> '2013–2017, 2019–2020, 2024'."""
    bagian, awal = [], 0
    for i in range(1, len(tahun) + 1):
        if i == len(tahun) or tahun[i] != tahun[i - 1] + 1:
            a, b = tahun[awal], tahun[i - 1]
            bagian.append(str(a) if a == b else f"{a}–{b}")
            awal = i
    return ", ".join(bagian)
