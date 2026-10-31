"""Uji halaman dan API terhadap CSV. Jalankan dari akar repo:  python -m tests.test_app"""

import re

import pandas as pd

import config
from app import app, norm


def main():
    c = app.test_client()
    t = pd.read_csv(config.TOPSIS_CSV)
    k = pd.read_csv(config.CLUSTERED_CSV)

    r = c.get("/")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    n_prior = int((k.cluster_id == 0).sum())
    jiwa = f"{int(round(t.jiwa_per_tahun.sum())):,}".replace(",", ".")
    assert f"{len(t)} Kecamatan" in html and f"{n_prior} Kecamatan" in html and jiwa in html
    assert f"{t.skor_topsis.min():.2f} – {t.skor_topsis.max():.2f}" in html
    top3 = k.sort_values("rank_topsis").head(3).kecamatan.str.title().tolist()
    assert all(n in html for n in top3), top3
    print("kartu ringkasan cocok dengan CSV | 3 teratas:", top3, "| jiwa/tahun:", jiwa)
    print("rentang tahun:", re.search(r"tahun data: ([^<]+)<", html).group(1))

    rows = c.get("/api/kecamatan").get_json()
    assert len(rows) == 42 and sorted(x["rank_topsis"] for x in rows) == list(range(1, 43))
    ukuran = pd.Series([x["cluster_id"] for x in rows]).value_counts().sort_index().tolist()
    assert ukuran == k.cluster_id.value_counts().sort_index().tolist()

    geo = c.get("/api/geojson").get_json()
    nama_geo = {norm(f["properties"]["kecamatan"]) for f in geo["features"]}
    assert nama_geo == {norm(x["kecamatan"]) for x in rows}, "nama GeoJSON dan CSV tidak cocok"
    print("API: 42 baris, ukuran klaster", ukuran, "| 42/42 poligon cocok dengan CSV")
    print("LULUS")


if __name__ == "__main__":
    main()
