"""Uji CLI: python -m src.pipeline harus menghasilkan CSV yang sama (secara numerik) dengan CSV di data/."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def sama(baru: pd.DataFrame, lama: pd.DataFrame):
    """Semua kolom CSV lama harus ada dan sama; kolom tambahan di hasil baru diperbolehkan
    (topsis_result.csv di repo dibuat sebelum kolom rumah pompa masuk ke dki_master.csv)."""
    assert set(lama.columns) <= set(baru.columns), set(lama.columns) - set(baru.columns)
    assert len(baru) == len(lama)
    a, b = baru[list(lama.columns)], lama
    for c in a.columns:
        if pd.api.types.is_numeric_dtype(a[c]):
            assert np.allclose(a[c], b[c], rtol=0, atol=1e-9, equal_nan=True), c
        else:
            assert (a[c].astype(str).values == b[c].astype(str).values).all(), c


def test_cli_sama_dengan_csv(tmp_path):
    r = subprocess.run([sys.executable, "-m", "src.pipeline", "--output", str(tmp_path)],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    for nama in ["topsis_result", "clustered_result"]:
        sama(pd.read_csv(tmp_path / f"{nama}.csv"), pd.read_csv(DATA / f"{nama}.csv"))
    sw0 = pd.read_csv(DATA / "k_sweep.csv")
    sw = pd.read_csv(tmp_path / "k_sweep.csv")
    assert np.allclose(sw[sw0.columns].values, sw0.values, atol=1e-6)

    m = json.load(open(tmp_path / "metrics.json", encoding="utf-8"))
    assert m["n_kecamatan"] == 42 and {"entropi", "sama", "pakar"} <= set(m["weights"])
    for w in m["weights"].values():
        assert len(w) == len(m["kriteria"]) == 8 and abs(sum(w) - 1) < 1e-9
    assert set(m["metrics_baseline"]) >= {"silhouette", "DBI", "CH", "ukuran_klaster"} and m["timestamp"]
    assert m["rentang_tahun"].startswith("2013") and m["rentang_tahun"].endswith("2024")


def test_cli_menolak_data_rusak(tmp_path):
    rusak = pd.read_csv(DATA / "dki_master.csv").drop(index=0)
    rusak.to_csv(tmp_path / "rusak.csv", index=False)
    r = subprocess.run([sys.executable, "-m", "src.pipeline", "--input", str(tmp_path / "rusak.csv"), "--output", str(tmp_path / "out")],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 1 and "Data ditolak" in r.stdout
    assert not (tmp_path / "out").exists(), "tidak boleh menulis apa pun jika data ditolak"
