"""Uji POST /api/simulasi terhadap topsis_result.csv. Jalankan: python -m pytest tests  (atau python -m tests.test_simulasi)"""

import numpy as np
import pandas as pd

import config
from app import app
from src.pipeline import CRIT_COLS, CRIT_TYPES
from src.topsis import topsis

t = pd.read_csv(config.TOPSIS_CSV)
c = app.test_client()


def kirim(bobot, preset="kustom"):
    return c.post("/api/simulasi", json={"bobot": bobot, "preset": preset})


def tabel(resp):
    return pd.DataFrame(resp.get_json()["hasil"]).set_index("kecamatan").loc[t.kecamatan]


def test_entropi_sama_dengan_csv():
    bobot = c.get("/api/kriteria").get_json()["bobot"]["entropi"]
    r = kirim(bobot, "entropi")
    assert r.status_code == 200
    h = tabel(r)
    assert (h.rank_baru.values == t.rank_topsis.values).all(), "peringkat berbeda dari topsis_result.csv"
    assert np.abs(h.skor_baru.values - t.skor_topsis.values).max() < 1e-6
    assert (h.delta == 0).all()


def test_sama_dan_pakar_sama_dengan_csv():
    bobot = c.get("/api/kriteria").get_json()["bobot"]
    for nama, kolom in [("sama", "skor_equal"), ("pakar", "skor_expert")]:
        h = tabel(kirim(bobot[nama], nama))
        assert np.abs(h.skor_baru.values - t[kolom].values).max() < 1e-6, nama


def test_kustom_dinormalisasi_dan_sama_dengan_python():
    mentah = [30, 0, 5, 10, 10, 25, 10, 10]          # jumlahnya 100, tapi 10x lipat pun harus sama
    r1, r2 = kirim(mentah), kirim([v * 10 for v in mentah])
    h1, h2 = tabel(r1), tabel(r2)
    assert np.allclose(h1.skor_baru, h2.skor_baru)
    assert abs(sum(r1.get_json()["bobot"]) - 1) < 1e-12
    py = topsis(t[CRIT_COLS].values.astype(float), np.array(mentah) / sum(mentah), CRIT_TYPES)[0]
    assert np.abs(h1.skor_baru.values - py).max() < 1e-9


def test_urut_menurut_perubahan_terbesar():
    h = pd.DataFrame(kirim([10, 15, 15, 10, 10, 20, 10, 10], "pakar").get_json()["hasil"])
    assert h.delta.abs().is_monotonic_decreasing and len(h) == 42


def test_payload_tidak_valid_ditolak():
    for bobot in [[1] * 7, [1] * 9, [-1] + [1] * 7, [0] * 8, ["a"] * 8, [True] * 8, None, "x"]:
        assert kirim(bobot).status_code == 400, bobot
    assert kirim([1] * 8, "aneh").status_code == 400
    assert c.post("/api/simulasi", data="bukan json").status_code == 400
    assert c.post("/api/simulasi", data='{"bobot": [NaN,1,1,1,1,1,1,1]}', content_type="application/json").status_code == 400


if __name__ == "__main__":
    for nama, fn in list(globals().items()):
        if nama.startswith("test_"):
            fn(); print("lulus:", nama)
