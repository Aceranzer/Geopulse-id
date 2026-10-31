"""Uji kesetaraan: run_pipeline(data/dki_master.csv) harus sama dengan CSV hasil notebook.

Jalankan dari akar repo:  python -m tests.test_equivalence
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

from src.pipeline import run_pipeline
from src.validate import validate_master, validate_result

DATA = Path(__file__).resolve().parent.parent / "data"


def main():
    master = pd.read_csv(DATA / "dki_master.csv")
    nama_geojson = gpd.read_file(DATA / "kecamatan_poly.geojson").kecamatan.tolist()
    galat = validate_master(master, nama_geojson)
    assert not galat, galat

    t, c, info = run_pipeline(master)
    t0 = pd.read_csv(DATA / "topsis_result.csv")
    c0 = pd.read_csv(DATA / "clustered_result.csv")

    for col in ["skor_topsis", "D_pos", "D_neg", "skor_equal", "skor_expert"]:
        selisih = np.abs(t[col].values - t0[col].values).max()
        print(f"{col:12s} selisih maks = {selisih:.2e}")
        assert selisih < 1e-9
    for col in ["rank_topsis", "rank_equal", "rank_expert"]:
        assert (t[col].values == t0[col].values).all(), col

    assert (c.kecamatan.values == c0.kecamatan.values).all()
    assert (c.cluster_id.values == c0.cluster_id.values).all(), "cluster_id berbeda"
    assert (c.cluster_name.values == c0.cluster_name.values).all()
    sel_sil = np.abs(c.silhouette_sample.values - c0.silhouette_sample.values).max()
    print(f"silhouette_sample selisih maks = {sel_sil:.2e}")
    assert sel_sil < 1e-9

    sweep0 = pd.read_csv(DATA / "k_sweep.csv", index_col="k")
    sel_sweep = np.abs(info["sweep"][sweep0.columns].values - sweep0.values).max()
    print(f"k_sweep selisih maks = {sel_sweep:.2e}")
    assert sel_sweep < 1e-6

    print("metrik:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in info["metrics"].items()})
    print("peringatan:", validate_result(c) or "tidak ada")
    print("LULUS: keluaran pipeline sama dengan CSV notebook")

    # data rusak harus ditolak
    rusak = master.drop(index=0)
    assert any("tepat 42" in e for e in validate_master(rusak, nama_geojson))
    rusak = master.copy(); rusak.loc[3, "tinggi_max_cm"] = np.nan
    assert any("kosong" in e for e in validate_master(rusak))
    rusak = master.copy(); rusak.loc[3, "jiwa_per_1000"] = 1500
    assert any("0 dan 1000" in e for e in validate_master(rusak))
    print("LULUS: data rusak (41 kecamatan, nilai kosong, jiwa_per_1000 > 1000) ditolak")


if __name__ == "__main__":
    main()
