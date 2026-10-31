"""Website Geopulse-ID (Flask). Semua angka dibaca dari file di folder data/."""

import json
import re
from datetime import datetime

import numpy as np
import pandas as pd
from flask import Flask, Response, abort, jsonify, redirect, render_template, request, url_for

import config
from src.pipeline import (CLUSTER_COLORS, CLUSTER_NAMES, CRIT_COLS, CRIT_TYPES, CRITERIA, K_FINAL,
                          SILHOUETTE_BATAS, W_EXPERT)
from src.recommend import CATATAN_VALIDASI, rekomendasi
from src.topsis import shannon_entropy_weights, topsis

app = Flask(__name__)
app.config["SECRET_KEY"] = config.SECRET_KEY or "dev-only-tidak-untuk-produksi"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# halaman yang sudah tersedia (menu header)
NAV = [("/", "Ringkasan Eksekutif"), ("/simulasi", "Simulasi Bobot"), ("/komparasi", "Komparasi Wilayah"),
       ("/klaster", "Klaster"), ("/metodologi", "Metodologi & Data")]


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


@app.context_processor
def inject_layout():
    return {"nav": NAV}


def versi_data():
    with open(config.METRICS_JSON, encoding="utf-8") as f:
        return json.load(f)["timestamp"].replace("T", " ")


def render_pdf(html, base_url):
    """HTML -> bytes PDF dengan WeasyPrint; None jika WeasyPrint/pustaka sistemnya tidak tersedia."""
    try:
        from weasyprint import HTML
    except (ImportError, OSError):      # OSError: pustaka Pango/GTK tidak ditemukan (mis. di Windows)
        return None
    return HTML(string=html, base_url=base_url).write_pdf()


@app.route("/")
def ringkasan():
    df = load_table()
    tahun = tahun_data()
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
                           colors=CLUSTER_COLORS, rek=rek, catatan=CATATAN_VALIDASI,
                           kriteria=[{"kolom": k, **v} for k, v in CRITERIA.items()])


@app.route("/metodologi")
def metodologi():
    with open(config.METRICS_JSON, encoding="utf-8") as f:
        metrics = json.load(f)
    w = bobot()
    tabel_bobot = [{"desc": c["desc"], "dimensi": c["dimensi"], "tipe": c["type"],
                    "entropi": w["entropi"][i] * 100, "sama": w["sama"][i] * 100, "pakar": w["pakar"][i] * 100}
                   for i, c in enumerate(CRITERIA.values())]
    terbesar = max(tabel_bobot, key=lambda r: r["entropi"])
    sw = pd.read_csv(config.SWEEP_CSV).set_index("k")
    tahun = tahun_data()
    return render_template(
        "metodologi.html", metrics=metrics["metrics"], timestamp=metrics["timestamp"], n_kecamatan=metrics["n_kecamatan"],
        tabel_bobot=tabel_bobot, terbesar=terbesar, k_final=K_FINAL,
        klaster=[{"id": int(i), "nama": CLUSTER_NAMES[int(i)], "n": n} for i, n in metrics["metrics"]["ukuran_klaster"].items()],
        sil_min=sw.silhouette.min(), sil_maks=sw.silhouette.max(), sil_k=sw.silhouette.loc[K_FINAL],
        n_tahun=len(tahun), rentang_tahun=rentang_tahun(tahun), batas=SILHOUETTE_BATAS, catatan=CATATAN_VALIDASI)


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
    return render_template("komparasi.html", colors=CLUSTER_COLORS, rek=rek, catatan=CATATAN_VALIDASI)


@app.route("/api/kecamatan")
def api_kecamatan():
    df = load_table()
    df["slug"] = df.kecamatan.map(slugify)
    kolom = ["rank_topsis", "kecamatan", "slug", "wilayah", "skor_topsis", "cluster_id", "cluster_name",
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


PRESET = {"entropi", "sama", "pakar", "kustom"}


def hitung_simulasi(w, preset):
    """Validasi bobot lalu hitung ulang TOPSIS. Mengembalikan (bobot ternormalisasi, tabel hasil); ValueError jika tidak valid."""
    if preset not in PRESET:
        raise ValueError("preset tidak dikenal")
    if not isinstance(w, list) or len(w) != len(CRIT_COLS) or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in w):
        raise ValueError(f"bobot harus berupa {len(CRIT_COLS)} angka")
    w = np.array(w, dtype=float)
    if not np.isfinite(w).all() or (w < 0).any() or w.sum() <= 0:
        raise ValueError("bobot harus angka tidak negatif dengan total lebih dari 0")
    w = w / w.sum()

    t = pd.read_csv(config.TOPSIS_CSV)
    X = t[CRIT_COLS].values.astype(float)
    skor = topsis(X, w, CRIT_TYPES)[0]
    rank_baru = pd.Series(skor).rank(ascending=False).astype(int).values
    hasil = pd.DataFrame({"kecamatan": t.kecamatan, "wilayah": t.wilayah, "rank_bawaan": t.rank_topsis,
                          "rank_baru": rank_baru, "skor_baru": skor})
    hasil["delta"] = hasil.rank_bawaan - hasil.rank_baru          # positif = naik peringkat
    hasil["selisih_mutlak"] = hasil.delta.abs()
    hasil = hasil.sort_values(["selisih_mutlak", "rank_baru"], ascending=[False, True]).drop(columns="selisih_mutlak")
    return w, hasil


@app.route("/api/simulasi", methods=["POST"])
def api_simulasi():
    """Hitung ulang TOPSIS dengan bobot dari pengguna; peringkat bawaan = bobot entropi (topsis_result.csv)."""
    payload = request.get_json(silent=True) or {}
    preset = payload.get("preset", "kustom")
    try:
        w, hasil = hitung_simulasi(payload.get("bobot"), preset)
    except ValueError as e:
        return jsonify({"galat": str(e)}), 400
    return jsonify({"preset": preset, "bobot": w.tolist(), "hasil": json.loads(hasil.to_json(orient="records"))})


NAMA_PRESET = {"entropi": "Entropi (bawaan)", "sama": "Sama rata", "pakar": "Pakar", "kustom": "Kustom"}


def profil_kecamatan(slug):
    """Data satu kecamatan untuk PDF/cetak; 404 jika slug tidak valid atau tidak ada di CSV."""
    if not re.fullmatch(r"[a-z0-9-]+", slug):
        abort(404)
    df = load_table()
    df["slug"] = df.kecamatan.map(slugify)
    baris = df[df.slug == slug]
    if baris.empty:
        abort(404)
    r = baris.iloc[0]
    return {
        "r": r, "n": len(df), "slug": slug,
        "kriteria": [{"desc": v["desc"], "satuan": v["satuan"], "nilai": r[k], "tipe": v["type"]} for k, v in CRITERIA.items()],
        "batas": bool(r.silhouette_sample < SILHOUETTE_BATAS),
        "rekomendasi": rekomendasi(r.cluster_id), "catatan": CATATAN_VALIDASI,
        "tanggal": datetime.now().strftime("%d-%m-%Y"), "versi": versi_data(),
    }


@app.route("/cetak/kecamatan/<slug>")
def cetak_kecamatan(slug):
    """Profil kecamatan sebagai halaman HTML siap cetak (cadangan jika PDF server tidak tersedia)."""
    return render_template("pdf/kecamatan.html", auto_print=request.args.get("cetak") == "1", **profil_kecamatan(slug))


@app.route("/ekspor/kecamatan/<slug>.pdf")
def pdf_kecamatan(slug):
    data = profil_kecamatan(slug)
    pdf = render_pdf(render_template("pdf/kecamatan.html", auto_print=False, **data), request.url_root)
    if pdf is None:   # WeasyPrint tidak tersedia: arahkan ke halaman cetak (Ctrl+P / Simpan sebagai PDF)
        return redirect(url_for("cetak_kecamatan", slug=slug, cetak=1))
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
    try:
        w, hasil = hitung_simulasi(bobot_mentah, preset)
    except ValueError as e:
        return jsonify({"galat": str(e)}), 400
    konteks = {
        "preset": NAMA_PRESET[preset], "hasil": hasil.to_dict("records"), "tanggal": datetime.now().strftime("%d-%m-%Y %H:%M"),
        "bobot": [{"desc": v["desc"], "tipe": v["type"], "persen": float(w[i] * 100)} for i, v in enumerate(CRITERIA.values())],
        "berubah": int((hasil.delta != 0).sum()), "versi": versi_data(),
    }
    pdf = render_pdf(render_template("pdf/simulasi.html", auto_print=False, **konteks), request.url_root)
    if pdf is None:   # cadangan: kirim halaman cetak yang otomatis membuka dialog cetak
        return render_template("pdf/simulasi.html", auto_print=True, **konteks)
    return Response(pdf, mimetype="application/pdf", headers={"Content-Disposition": "attachment; filename=simulasi-bobot.pdf"})


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
