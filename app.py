"""Website Geopulse-ID (Flask). Semua angka dibaca dari file di folder data/."""

import json
import re

import pandas as pd
from flask import Flask, jsonify, render_template

import config
from src.pipeline import (CLUSTER_COLORS, CRIT_COLS, CRITERIA, K_FINAL, SILHOUETTE_BATAS,
                          W_EXPERT)
from src.recommend import rekomendasi
from src.topsis import shannon_entropy_weights

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY or "dev-only-tidak-untuk-produksi"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# halaman yang sudah tersedia (menu header)
NAV = [("/", "Ringkasan Eksekutif"), ("/simulasi", "Simulasi Bobot"), ("/komparasi", "Komparasi Wilayah"), ("/klaster", "Klaster")]


def norm(nama):
    """Normalisasi nama kecamatan untuk mencocokkan CSV dan GeoJSON."""
    return re.sub(r"\s+", " ", str(nama)).strip().upper()


def load_table():
    """Gabungan topsis_result.csv dan clustered_result.csv, urut menurut peringkat."""
    t = pd.read_csv(config.TOPSIS_CSV)
    c = pd.read_csv(config.CLUSTERED_CSV)
    t["key"], c["key"] = t.kecamatan.map(norm), c.kecamatan.map(norm)
    df = t.merge(c[["key", "cluster_id", "cluster_name", "silhouette_sample"]], on="key", how="left", validate="1:1")
    assert df.cluster_id.notna().all(), "ada kecamatan tanpa klaster"
    return df.sort_values("rank_topsis").reset_index(drop=True)


def tahun_data():
    """Tahun yang tersedia pada data kejadian banjir (dari nama file di data/raw)."""
    files = config.RAW_DIR.glob("*kejadian-bencana-banjir*.xls")
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


@app.context_processor
def inject_layout():
    return {"nav": NAV}


@app.route("/")
def ringkasan():
    df = load_table()
    tahun = tahun_data()
    stats = {
        "n_kecamatan": len(df),
        "n_kota": df.wilayah.nunique(),
        "n_prioritas": int((df.cluster_id == 0).sum()),
        "jiwa_per_tahun": int(round(df.jiwa_per_tahun.sum())),
        "skor_min": df.skor_topsis.min(),
        "skor_maks": df.skor_topsis.max(),
        "n_tahun": len(tahun),
        "rentang_tahun": rentang_tahun(tahun),
    }
    return render_template("ringkasan.html", stats=stats, top3=df.head(3).to_dict("records"),
                           colors=CLUSTER_COLORS)


@app.route("/simulasi")
def simulasi():
    return render_template("simulasi.html")


@app.route("/klaster")
def klaster():
    return render_template("klaster.html", colors=CLUSTER_COLORS, k_final=K_FINAL, batas=SILHOUETTE_BATAS)


@app.route("/komparasi")
def komparasi():
    # rekomendasi per klaster; None = belum ditetapkan tim
    rek = {i: rekomendasi(i) for i in range(K_FINAL)}
    return render_template("komparasi.html", colors=CLUSTER_COLORS, rek=rek)


@app.route("/api/kecamatan")
def api_kecamatan():
    df = load_table()
    kolom = ["rank_topsis", "kecamatan", "wilayah", "skor_topsis", "cluster_id", "cluster_name",
             "silhouette_sample", "jiwa_per_tahun"] + list(CRITERIA)
    kolom = list(dict.fromkeys(kolom))
    return jsonify(json.loads(df[kolom].to_json(orient="records")))


def bobot():
    """Bobot entropi (dihitung dari data), sama rata, dan pakar."""
    X = pd.read_csv(config.TOPSIS_CSV)[CRIT_COLS].values.astype(float)
    return {"entropi": shannon_entropy_weights(X).tolist(),
            "sama": [1 / len(CRIT_COLS)] * len(CRIT_COLS),
            "pakar": W_EXPERT.tolist()}


@app.route("/api/kriteria")
def api_kriteria():
    t = pd.read_csv(config.TOPSIS_CSV)
    kriteria = [{"kolom": k, **v} for k, v in CRITERIA.items()]
    data = json.loads(t[["kecamatan"] + CRIT_COLS].to_json(orient="records"))
    return jsonify({"kriteria": kriteria, "bobot": bobot(), "data": data})


@app.route("/api/klaster")
def api_klaster():
    df = load_table()
    rata_semua = df[CRIT_COLS + ["skor_topsis"]].mean()
    hasil = []
    for cid, g in df.groupby("cluster_id"):
        rata = g[CRIT_COLS + ["skor_topsis"]].mean()
        anggota = [{"kecamatan": r.kecamatan, "rank": int(r.rank_topsis), "silhouette": r.silhouette_sample,
                    "batas": bool(r.silhouette_sample < SILHOUETTE_BATAS)} for r in g.itertuples()]
        hasil.append({"cluster_id": int(cid), "nama": g.cluster_name.iloc[0], "warna": CLUSTER_COLORS[int(cid)],
                      "n": len(g), "rata": rata.to_dict(), "anggota": anggota})
    return jsonify({"klaster": hasil, "rata_semua": rata_semua.to_dict(),
                    "kriteria": [{"kolom": k, **v} for k, v in CRITERIA.items()]})


@app.route("/api/sweep")
def api_sweep():
    sw = pd.read_csv(config.SWEEP_CSV)
    return jsonify({"k_final": K_FINAL, "sweep": json.loads(sw.to_json(orient="records"))})


@app.route("/api/geojson")
def api_geojson():
    with open(config.GEOJSON, encoding="utf-8") as f:
        return jsonify(json.load(f))


if __name__ == "__main__":
    app.run(debug=False)
