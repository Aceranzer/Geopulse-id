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
    # Fase 3: klaster, sweep, kriteria, komparasi
    d = c.get("/api/klaster").get_json()
    assert sum(x["n"] for x in d["klaster"]) == 42
    for x in d["klaster"]:
        g = t.merge(k[["kecamatan", "cluster_id", "silhouette_sample"]], on="kecamatan")
        g = g[g.cluster_id == x["cluster_id"]]
        assert abs(x["rata"]["tinggi_max_cm"] - g.tinggi_max_cm.mean()) < 1e-9
        assert x["n"] == len(g)
        assert sum(m["batas"] for m in x["anggota"]) == int((g.silhouette_sample < 0.1).sum())
    n_batas = sum(m["batas"] for x in d["klaster"] for m in x["anggota"])
    print("klaster:", [x["n"] for x in d["klaster"]], "| kecamatan batas:", n_batas)

    sw = c.get("/api/sweep").get_json()
    assert [r["k"] for r in sw["sweep"]] == [2, 3, 4, 5, 6, 7] and sw["k_final"] == 4

    kr = c.get("/api/kriteria").get_json()
    assert len(kr["kriteria"]) == 8 and [x["type"] for x in kr["kriteria"]].count("cost") == 1
    for nama, w in kr["bobot"].items():
        assert abs(sum(w) - 1) < 1e-9, nama
    assert len(kr["data"]) == 42
    print("bobot entropi:", [round(x, 3) for x in kr["bobot"]["entropi"]])

    for url in ["/klaster", "/komparasi", "/simulasi"]:
        assert c.get(url).status_code == 200, url
    # aturan rekomendasi belum ditetapkan tim -> halaman mengirim null (placeholder), bukan teks karangan
    assert "window.REKOMENDASI" in c.get("/komparasi").get_data(as_text=True)
    print("LULUS")


test_halaman_dan_api = main   # agar pytest ikut menjalankannya


if __name__ == "__main__":
    main()
