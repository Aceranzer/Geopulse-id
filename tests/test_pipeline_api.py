"""Uji POST /api/pipeline (bobot aktif): kesetaraan dengan CSV, cache, validasi. Jalankan: python -m pytest tests/test_pipeline_api.py"""

import time

import numpy as np
import pandas as pd

import app as aplikasi
import config
from app import app, bobot, dapatkan_payload, hitung_aktif, kunci_bobot, validasi_bobot
from src.pipeline import CRIT_COLS, CRIT_TYPES
from src.topsis import topsis

c = app.test_client()
t = pd.read_csv(config.TOPSIS_CSV).set_index("kecamatan")
k = pd.read_csv(config.CLUSTERED_CSV).set_index("kecamatan")
PAKAR = [10, 15, 15, 10, 10, 20, 10, 10]


def tabel(payload):
    return pd.DataFrame(payload["kecamatan"]).set_index("kecamatan").loc[t.index]


def test_hitung_asli_dengan_bobot_entropi_sama_dengan_csv():
    """Lewati cache: pipeline sungguhan dengan bobot entropi harus identik dengan CSV baseline."""
    h = tabel(hitung_aktif(validasi_bobot(bobot()["entropi"])))
    assert np.abs(h.skor_topsis.values - t.skor_topsis.values).max() < 1e-9
    assert (h.rank_topsis.values == t.rank_topsis.values).all()
    assert (h.cluster_id.values == k.loc[t.index].cluster_id.values).all()
    assert (h.delta == 0).all()


def test_endpoint_bobot_entropi_sama_dengan_baseline():
    r = c.post("/api/pipeline", json={"bobot": bobot()["entropi"], "preset": "entropi"})
    assert r.status_code == 200
    h = tabel(r.get_json())
    assert (h.rank_topsis.values == t.rank_topsis.values).all()
    assert (h.cluster_id.values == k.loc[t.index].cluster_id.values).all()


def test_bobot_pakar_skor_sama_dengan_csv_dan_klaster_dihitung_ulang():
    d = c.post("/api/pipeline", json={"bobot": PAKAR, "preset": "pakar"}).get_json()
    h = tabel(d)
    assert np.abs(h.skor_topsis.values - t.skor_expert.values).max() < 1e-6          # sama dengan kolom skor_expert
    ukuran = pd.Series([r["cluster_id"] for r in d["kecamatan"]]).value_counts().sort_index()
    assert list(ukuran.index) == [0, 1, 2, 3] and ukuran.sum() == 42
    rata = pd.DataFrame(d["kecamatan"]).groupby("cluster_id").skor_topsis.mean()
    assert rata.is_monotonic_decreasing, "klaster 0 harus berskor rata-rata tertinggi"
    assert [r["n"] for r in d["klaster"]["klaster"]] == ukuran.tolist()
    assert len(d["sweep"]) == 6 and d["metrics"]["ukuran_klaster"]
    assert (h.delta == h.rank_bawaan - h.rank_topsis).all() and (h.delta != 0).any()


def test_bobot_dinormalisasi_kustom_sama_dengan_python():
    mentah = [30, 0, 5, 10, 10, 25, 10, 10]
    d1 = c.post("/api/pipeline", json={"bobot": mentah}).get_json()
    d2 = c.post("/api/pipeline", json={"bobot": [v * 10 for v in mentah]}).get_json()
    assert abs(sum(d1["bobot"]) - 1) < 1e-12 and np.allclose(d1["bobot"], d2["bobot"])
    py = topsis(t[CRIT_COLS].values.astype(float), np.array(mentah) / sum(mentah), CRIT_TYPES)[0]
    assert np.abs(tabel(d1).skor_topsis.values - py).max() < 1e-9


def test_cache_dan_lru(monkeypatch):
    panggilan = []
    asli = aplikasi.hitung_aktif
    monkeypatch.setattr(aplikasi, "hitung_aktif", lambda w: (panggilan.append(1), asli(w))[1])
    aplikasi._CACHE.clear()
    w = validasi_bobot([1, 2, 3, 4, 5, 6, 7, 8])
    dapatkan_payload(w); dapatkan_payload(w)
    assert len(panggilan) == 1, "panggilan kedua dengan bobot sama harus dari cache"
    dapatkan_payload(validasi_bobot(bobot()["entropi"]))
    assert len(panggilan) == 1, "bobot entropi dilayani dari baseline tanpa menghitung"
    # tidak melebihi batas dan baseline tidak tergusur
    monkeypatch.setattr(aplikasi, "hitung_aktif", lambda w: {"palsu": float(w[0])})
    for i in range(aplikasi.CACHE_MAKS + 5):
        dapatkan_payload(validasi_bobot([1 + i, 1, 1, 1, 1, 1, 1, 1]))
    assert len(aplikasi._CACHE) == aplikasi.CACHE_MAKS
    assert kunci_bobot(validasi_bobot(bobot()["entropi"])) == aplikasi._KUNCI_BAWAAN
    aplikasi._CACHE.clear()


def test_latensi_wajar():
    aplikasi._CACHE.clear()
    c.post("/api/pipeline", json={"bobot": [9, 1, 1, 1, 1, 1, 1, 1]})        # pemanasan
    t0 = time.time()
    r = c.post("/api/pipeline", json={"bobot": [1, 9, 1, 1, 1, 1, 1, 1]})
    dt = time.time() - t0
    print(f"latensi hitung baru: {dt:.2f} detik")
    assert r.status_code == 200 and dt < 5, dt          # target plan < 2 detik; batas tes longgar agar tidak rapuh
    t0 = time.time(); c.post("/api/pipeline", json={"bobot": [1, 9, 1, 1, 1, 1, 1, 1]}); assert time.time() - t0 < 0.5


def test_payload_tidak_valid_ditolak():
    for bobot_salah in [[1] * 7, [1] * 9, [-1] + [1] * 7, [0] * 8, ["a"] * 8, [True] * 8, None, "x"]:
        assert c.post("/api/pipeline", json={"bobot": bobot_salah}).status_code == 400, bobot_salah
    assert c.post("/api/pipeline", json={"bobot": PAKAR, "preset": "aneh"}).status_code == 400
    assert c.post("/api/pipeline", data="bukan json").status_code == 400
    assert c.post("/api/pipeline", data='{"bobot": [NaN,1,1,1,1,1,1,1]}', content_type="application/json").status_code == 400
    assert c.get("/api/pipeline").status_code == 405
    assert c.post("/api/simulasi", json={"bobot": PAKAR}).status_code == 404       # endpoint lama sudah dihapus


def test_api_baca_saja_tetap_baseline():
    rows = c.get("/api/kecamatan").get_json()
    assert len(rows) == 42 and all("slug" in r and r["delta"] == 0 for r in rows)
    assert c.get("/api/klaster").get_json()["klaster"] and len(c.get("/api/sweep").get_json()["sweep"]) == 6
