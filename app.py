"""Website Geopulse-ID (Flask). Semua angka dibaca dari file di folder data/."""

import hashlib
import json
import re
import threading
from collections import OrderedDict
from datetime import datetime

import numpy as np
import pandas as pd
from flask import Flask, Response, abort, jsonify, redirect, render_template, request, url_for

import config
from src.pipeline import (CLUSTER_COLORS, CLUSTER_NAMES, CRIT_COLS, CRITERIA, K_FINAL, SILHOUETTE_BATAS,
                          W_EXPERT, run_pipeline)
from src.recommend import CATATAN_VALIDASI, SUMBER, rekomendasi
from src.tahun import rentang_tahun, tahun_data
from src.topsis import shannon_entropy_weights

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY or "dev-only-tidak-untuk-produksi"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

GITHUB_URL = "https://github.com/Aceranzer/Geopulse-id"

# halaman yang tersedia (menu header)
NAV = [("/", "Dashboard"), ("/simulasi", "Simulasi Bobot"), ("/komparasi", "Komparasi Wilayah"),
       ("/klaster", "Klaster"), ("/metodologi", "Metodologi & Data")]

PRESET = {"entropi", "sama", "pakar", "kustom"}
NAMA_PRESET = {"entropi": "Entropi (bawaan)", "sama": "Sama rata", "pakar": "Pakar", "kustom": "Kustom"}


# ---------------------------------------------------------------- utilitas

def norm(nama):
    """Normalisasi nama kecamatan untuk mencocokkan CSV dan GeoJSON."""
    return re.sub(r"\s+", " ", str(nama)).strip().upper()


def slugify(nama):
    """KEBON JERUK -> kebon-jeruk (dipakai di URL ekspor)."""
    return re.sub(r"[^a-z0-9]+", "-", str(nama).lower()).strip("-")


def angka(v):
    """Format angka gaya Indonesia: 20455.3 -> 20.455 ; 3.1337 -> 3,13."""
    s = f"{v:,.0f}" if abs(v) >= 100 else f"{v:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


app.jinja_env.filters["angka"] = angka
# CSS PDF disisipkan inline agar WeasyPrint tidak perlu mengunduh berkas dari server yang sama (bisa deadlock di worker tunggal)
app.jinja_env.globals["pdf_css"] = lambda: (config.BASE_DIR / "static" / "css" / "pdf.css").read_text(encoding="utf-8")


def baca_metrics():
    with open(config.METRICS_JSON, encoding="utf-8") as f:
        return json.load(f)


def versi_data():
    return baca_metrics()["timestamp"].replace("T", " ")


@app.context_processor
def inject_layout():
    """Data yang tampil di setiap halaman: menu, metadata data (footer), tautan repo."""
    tahun = tahun_data(config.RAW_DIR)
    return {"nav": NAV, "github_url": GITHUB_URL,
            "meta_data": {"n_tahun": len(tahun), "tahun_awal": tahun[0], "tahun_akhir": tahun[-1],
                          "rentang": rentang_tahun(tahun), "versi": versi_data()}}


def render_pdf(html, base_url):
    """HTML -> bytes PDF dengan WeasyPrint; None jika WeasyPrint/pustaka sistemnya tidak tersedia."""
    try:
        from weasyprint import HTML
    except (ImportError, OSError):      # OSError: pustaka Pango/GTK tidak ditemukan (mis. di Windows)
        return None
    return HTML(string=html, base_url=base_url).write_pdf()


# ---------------------------------------------------------------- data dasar (bobot entropi)

def load_table():
    """Gabungan topsis_result.csv dan clustered_result.csv, urut menurut peringkat."""
    t = pd.read_csv(config.TOPSIS_CSV)
    c = pd.read_csv(config.CLUSTERED_CSV)
    t["key"], c["key"] = t.kecamatan.map(norm), c.kecamatan.map(norm)
    df = t.merge(c[["key", "cluster_id", "cluster_name", "silhouette_sample"]], on="key", how="left", validate="1:1")
    assert df.cluster_id.notna().all(), "ada kecamatan tanpa klaster"
    return df.sort_values("rank_topsis").reset_index(drop=True)


def bobot():
    """Bobot entropi (dihitung dari data), sama rata, dan pakar."""
    X = pd.read_csv(config.TOPSIS_CSV)[CRIT_COLS].values.astype(float)
    return {"entropi": shannon_entropy_weights(X).tolist(),
            "sama": [1 / len(CRIT_COLS)] * len(CRIT_COLS),
            "pakar": W_EXPERT.tolist()}


# ---------------------------------------------------------------- pipeline dengan bobot aktif + cache

def validasi_bobot(w):
    """List 8 angka tidak negatif dengan total > 0 -> array ternormalisasi (jumlah 1). ValueError jika tidak valid."""
    if not isinstance(w, list) or len(w) != len(CRIT_COLS) or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in w):
        raise ValueError(f"bobot harus berupa {len(CRIT_COLS)} angka")
    w = np.array(w, dtype=float)
    if not np.isfinite(w).all() or (w < 0).any() or w.sum() <= 0:
        raise ValueError("bobot harus angka tidak negatif dengan total lebih dari 0")
    return w / w.sum()


def kunci_bobot(w):
    return hashlib.sha1(",".join(f"{v:.6f}" for v in w).encode()).hexdigest()


def baris_kecamatan(df):
    """DataFrame hasil (sudah bergabung dengan klaster) -> daftar dict untuk JSON, urut menurut peringkat."""
    df = df.sort_values("rank_topsis").copy()
    df["slug"] = df.kecamatan.map(slugify)
    kolom = list(dict.fromkeys(["rank_topsis", "rank_bawaan", "delta", "kecamatan", "slug", "wilayah", "skor_topsis", "cluster_id",
                                "cluster_name", "silhouette_sample", "jiwa_per_tahun"] + list(CRITERIA)))
    return json.loads(df[kolom].to_json(orient="records"))


def ringkas_klaster(df):
    """Ringkasan per klaster (anggota, rata-rata kriteria) untuk halaman Klaster."""
    rata_semua = df[CRIT_COLS + ["skor_topsis"]].mean()
    hasil = []
    for cid, g in df.groupby("cluster_id"):
        rata = g[CRIT_COLS + ["skor_topsis"]].mean()
        anggota = [{"kecamatan": r.kecamatan, "rank": int(r.rank_topsis), "silhouette": r.silhouette_sample,
                    "batas": bool(r.silhouette_sample < SILHOUETTE_BATAS)} for r in g.itertuples()]
        hasil.append({"cluster_id": int(cid), "nama": g.cluster_name.iloc[0], "warna": CLUSTER_COLORS[int(cid)],
                      "n": len(g), "rata": rata.to_dict(), "anggota": anggota})
    return {"klaster": hasil, "rata_semua": rata_semua.to_dict(),
            "kriteria": [{"kolom": k, **v} for k, v in CRITERIA.items()]}


def payload_baseline():
    """Hasil dengan bobot entropi, dibaca langsung dari CSV (bukan dihitung ulang)."""
    df = load_table()
    df["rank_bawaan"], df["delta"] = df.rank_topsis, 0
    sweep = json.loads(pd.read_csv(config.SWEEP_CSV).to_json(orient="records"))
    return {"bobot": bobot()["entropi"], "kecamatan": baris_kecamatan(df), "klaster": ringkas_klaster(df),
            "sweep": sweep, "k_final": K_FINAL, "metrics": baca_metrics()["metrics_baseline"]}


def hitung_aktif(w):
    """Jalankan pipeline penuh (TOPSIS + K-Means + sweep k=2..7) dengan bobot w (sudah ternormalisasi)."""
    master = pd.read_csv(config.DATA_DIR / "dki_master.csv")
    topsis_df, clustered_df, info = run_pipeline(master, w)
    df = topsis_df.merge(clustered_df[["kecamatan", "cluster_id", "cluster_name", "silhouette_sample"]], on="kecamatan")
    bawaan = pd.read_csv(config.TOPSIS_CSV).set_index("kecamatan").rank_topsis
    df["rank_bawaan"] = df.kecamatan.map(bawaan)
    df["delta"] = df.rank_bawaan - df.rank_topsis             # positif = naik peringkat
    return {"bobot": w.tolist(), "kecamatan": baris_kecamatan(df), "klaster": ringkas_klaster(df),
            "sweep": json.loads(info["sweep"].reset_index().to_json(orient="records")), "k_final": K_FINAL,
            "metrics": info["metrics"]}


CACHE_MAKS = 20
_CACHE = OrderedDict()              # kunci SHA1 bobot -> payload (LRU, maks 20)
_KUNCI_BAWAAN = kunci_bobot(bobot()["entropi"])
_BAWAAN = payload_baseline()        # diisi saat aplikasi mulai; tidak ikut tergusur dari cache
_KUNCI = threading.Lock()


def dapatkan_payload(w):
    """Payload untuk bobot w (ternormalisasi); memakai cache, hitung ulang hanya jika belum pernah dihitung."""
    kunci = kunci_bobot(w)
    if kunci == _KUNCI_BAWAAN:
        return _BAWAAN
    with _KUNCI:
        if kunci in _CACHE:
            _CACHE.move_to_end(kunci)
            return _CACHE[kunci]
    hasil = hitung_aktif(w)
    with _KUNCI:
        _CACHE[kunci] = hasil
        while len(_CACHE) > CACHE_MAKS:
            _CACHE.popitem(last=False)
    return hasil


@app.route("/api/pipeline", methods=["POST"])
def api_pipeline():
    """Hasil lengkap (peringkat, klaster, sweep, metrik) untuk bobot dari pengguna."""
    payload = request.get_json(silent=True) or {}
    preset = payload.get("preset", "kustom")
    if preset not in PRESET:
        return jsonify({"galat": "preset tidak dikenal"}), 400
    try:
        w = validasi_bobot(payload.get("bobot"))
    except ValueError as e:
        return jsonify({"galat": str(e)}), 400
    return jsonify({**dapatkan_payload(w), "preset": preset})


# ---------------------------------------------------------------- halaman

@app.route("/")
def ringkasan():
    df = load_table()
    tahun = tahun_data(config.RAW_DIR)
    stats = {
        "n_kecamatan": len(df),
        "n_kota": df.wilayah.nunique(),
        "n_prioritas": int((df.cluster_id == 0).sum()),
        "kejadian_rata": df.kejadian_per_tahun.mean(),
        "skor_min": df.skor_topsis.min(),
        "skor_maks": df.skor_topsis.max(),
        "n_tahun": len(tahun),
        "rentang_tahun": rentang_tahun(tahun),
    }
    rek = {i: rekomendasi(i) for i in range(K_FINAL)}
    return render_template("ringkasan.html", stats=stats, top3=df.head(3).to_dict("records"),
                           colors=CLUSTER_COLORS, rek=rek, catatan=CATATAN_VALIDASI, sumber_rek=SUMBER,
                           kriteria=[{"kolom": k, **v} for k, v in CRITERIA.items()])


def interpretasi_kriteria():
    """Arti tiap kriteria + contoh kecamatan bernilai tertinggi dan terendah (dari topsis_result.csv)."""
    t = pd.read_csv(config.TOPSIS_CSV).set_index("kecamatan")
    hasil = []
    for kolom, v in CRITERIA.items():
        s = t[kolom].sort_values(ascending=False)
        tinggi = ", ".join(f"{n.title()} ({angka(x)})" for n, x in s.head(2).items())
        minimum = s.min()
        n_min = int((s == minimum).sum())
        if n_min > 2:     # banyak kecamatan berbagi nilai terendah (mis. 0 alat peringatan dini)
            rendah = f"{n_min} kecamatan bernilai {angka(minimum)}"
        else:
            rendah = ", ".join(f"{n.title()} ({angka(x)})" for n, x in s.tail(2)[::-1].items())
        hasil.append({"desc": v["desc"], "dimensi": v["dimensi"], "satuan": v["satuan"],
                      "arah": "Makin sedikit, makin berisiko" if v["type"] == "cost" else "Makin tinggi, makin berisiko",
                      "tinggi": tinggi, "rendah": rendah})
    return hasil


@app.route("/metodologi")
def metodologi():
    metrics = baca_metrics()
    w = bobot()
    tabel_bobot = [{"desc": c["desc"], "dimensi": c["dimensi"], "tipe": c["type"],
                    "entropi": w["entropi"][i] * 100, "sama": w["sama"][i] * 100, "pakar": w["pakar"][i] * 100}
                   for i, c in enumerate(CRITERIA.values())]
    terbesar = max(tabel_bobot, key=lambda r: r["entropi"])
    sw = pd.read_csv(config.SWEEP_CSV).set_index("k")
    mb = metrics["metrics_baseline"]
    return render_template(
        "metodologi.html", metrics=mb, timestamp=metrics["timestamp"], n_kecamatan=metrics["n_kecamatan"],
        tabel_bobot=tabel_bobot, terbesar=terbesar, k_final=K_FINAL, interpretasi=interpretasi_kriteria(),
        klaster=[{"id": int(i), "nama": CLUSTER_NAMES[int(i)], "n": n} for i, n in mb["ukuran_klaster"].items()],
        sil_min=sw.silhouette.min(), sil_maks=sw.silhouette.max(), sil_k=sw.silhouette.loc[K_FINAL],
        n_tahun=len(tahun_data(config.RAW_DIR)), rentang_tahun=metrics["rentang_tahun"],
        batas=SILHOUETTE_BATAS, catatan=CATATAN_VALIDASI)


@app.route("/simulasi")
def simulasi():
    return render_template("simulasi.html")


@app.route("/klaster")
def klaster():
    mb = baca_metrics()["metrics_baseline"]
    baseline = [{"nama": CLUSTER_NAMES[int(i)], "n": n} for i, n in mb["ukuran_klaster"].items()]
    return render_template("klaster.html", colors=CLUSTER_COLORS, k_final=K_FINAL, batas=SILHOUETTE_BATAS, baseline=baseline)


@app.route("/komparasi")
def komparasi():
    rek = {i: rekomendasi(i) for i in range(K_FINAL)}
    return render_template("komparasi.html", colors=CLUSTER_COLORS, rek=rek, catatan=CATATAN_VALIDASI, sumber_rek=SUMBER)


# ---------------------------------------------------------------- API baca-saja (bobot bawaan)

@app.route("/api/kecamatan")
def api_kecamatan():
    return jsonify(_BAWAAN["kecamatan"])


@app.route("/api/kriteria")
def api_kriteria():
    t = pd.read_csv(config.TOPSIS_CSV)
    kriteria = [{"kolom": k, **v} for k, v in CRITERIA.items()]
    data = json.loads(t[["kecamatan"] + CRIT_COLS].to_json(orient="records"))
    return jsonify({"kriteria": kriteria, "bobot": bobot(), "data": data})


@app.route("/api/klaster")
def api_klaster():
    return jsonify(_BAWAAN["klaster"])


@app.route("/api/sweep")
def api_sweep():
    return jsonify({"k_final": K_FINAL, "sweep": _BAWAAN["sweep"]})


@app.route("/api/geojson")
def api_geojson():
    with open(config.GEOJSON, encoding="utf-8") as f:
        return jsonify(json.load(f))


# ---------------------------------------------------------------- cetak dan PDF

def bobot_dari_query():
    """?w=10,15,... (bobot aktif, opsional) -> array ternormalisasi atau None. 400 jika tidak valid."""
    mentah = request.args.get("w")
    if not mentah:
        return None
    try:
        return validasi_bobot([float(v) for v in mentah.split(",")])
    except ValueError:
        abort(400)


def profil_kecamatan(slug, w=None, preset=None):
    """Data satu kecamatan untuk PDF/cetak; 404 jika slug tidak valid atau tidak ada di CSV."""
    if not re.fullmatch(r"[a-z0-9-]+", slug):
        abort(404)
    payload = dapatkan_payload(w) if w is not None else _BAWAAN
    baris = [r for r in payload["kecamatan"] if r["slug"] == slug]
    if not baris:
        abort(404)
    r = baris[0]
    return {
        "r": r, "n": len(payload["kecamatan"]), "slug": slug,
        "kriteria": [{"desc": v["desc"], "satuan": v["satuan"], "nilai": r[k], "tipe": v["type"]} for k, v in CRITERIA.items()],
        "batas": bool(r["silhouette_sample"] < SILHOUETTE_BATAS),
        "rekomendasi": rekomendasi(r["cluster_id"]), "catatan": CATATAN_VALIDASI, "sumber_rek": SUMBER,
        "bobot_aktif": NAMA_PRESET.get(preset, "Kustom") if w is not None else None,
        "tanggal": datetime.now().strftime("%d-%m-%Y"), "versi": versi_data(),
    }


@app.route("/cetak/kecamatan/<slug>")
def cetak_kecamatan(slug):
    """Profil kecamatan sebagai halaman HTML siap cetak (cadangan jika PDF server tidak tersedia)."""
    data = profil_kecamatan(slug, bobot_dari_query(), request.args.get("p"))
    return render_template("pdf/kecamatan.html", auto_print=request.args.get("cetak") == "1", **data)


@app.route("/ekspor/kecamatan/<slug>.pdf")
def pdf_kecamatan(slug):
    w = bobot_dari_query()
    data = profil_kecamatan(slug, w, request.args.get("p"))
    pdf = render_pdf(render_template("pdf/kecamatan.html", auto_print=False, **data), request.url_root)
    if pdf is None:   # WeasyPrint tidak tersedia: arahkan ke halaman cetak (Ctrl+P / Simpan sebagai PDF)
        return redirect(url_for("cetak_kecamatan", slug=slug, cetak=1, **request.args.to_dict()))
    return Response(pdf, mimetype="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=profil-{slug}.pdf"})


def payload_simulasi():
    """Payload dari JSON atau dari form (kolom 'payload' berisi JSON) -> (bobot, preset)."""
    p = request.get_json(silent=True)
    if p is None and request.form.get("payload"):
        try:
            p = json.loads(request.form["payload"])
        except ValueError:
            p = None
    p = p if isinstance(p, dict) else {}
    return p.get("bobot"), p.get("preset", "kustom")


@app.route("/ekspor/simulasi.pdf", methods=["POST"])
def pdf_simulasi():
    bobot_mentah, preset = payload_simulasi()
    if preset not in PRESET:
        return jsonify({"galat": "preset tidak dikenal"}), 400
    try:
        w = validasi_bobot(bobot_mentah)
    except ValueError as e:
        return jsonify({"galat": str(e)}), 400
    baris = dapatkan_payload(w)["kecamatan"]
    hasil = sorted(({"kecamatan": r["kecamatan"], "wilayah": r["wilayah"], "rank_bawaan": r["rank_bawaan"],
                     "rank_baru": r["rank_topsis"], "skor_baru": r["skor_topsis"], "delta": r["delta"]} for r in baris),
                   key=lambda r: (-abs(r["delta"]), r["rank_baru"]))
    konteks = {
        "preset": NAMA_PRESET[preset], "hasil": hasil, "tanggal": datetime.now().strftime("%d-%m-%Y %H:%M"),
        "bobot": [{"desc": v["desc"], "tipe": v["type"], "persen": float(w[i] * 100)} for i, v in enumerate(CRITERIA.values())],
        "berubah": sum(1 for r in hasil if r["delta"] != 0), "versi": versi_data(),
    }
    pdf = render_pdf(render_template("pdf/simulasi.html", auto_print=False, **konteks), request.url_root)
    if pdf is None:   # cadangan: kirim halaman cetak yang otomatis membuka dialog cetak
        return render_template("pdf/simulasi.html", auto_print=True, **konteks)
    return Response(pdf, mimetype="application/pdf", headers={"Content-Disposition": "attachment; filename=simulasi-bobot.pdf"})


if __name__ == "__main__":
    app.run(debug=False)
