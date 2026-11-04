"""Uji profil kecamatan, ekspor PDF, dan cadangan cetak. Jalankan: python -m pytest tests/test_ekspor.py"""

import json
import re

import pandas as pd
import pytest

import app as aplikasi
import config
from app import angka, app, slugify
from src.pipeline import CRITERIA

c = app.test_client()
t = pd.read_csv(config.TOPSIS_CSV)


def test_slug_unik_dan_valid():
    rows = c.get("/api/kecamatan").get_json()
    slugs = [r["slug"] for r in rows]
    assert len(set(slugs)) == 42 and all(re.fullmatch(r"[a-z0-9-]+", s) for s in slugs)
    assert slugify("KEBON JERUK") == "kebon-jeruk" and slugify(" Mampang  Prapatan ") == "mampang-prapatan"


def test_format_angka():
    assert angka(20455.3) == "20.455" and angka(3.1337) == "3,13" and angka(0) == "0,00" and angka(160) == "160"


def test_halaman_cetak_memuat_data_dari_csv():
    r = c.get("/cetak/kecamatan/kebon-jeruk")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    row = t[t.kecamatan == "KEBON JERUK"].iloc[0]
    assert f"#{row.rank_topsis} dari 42" in html and f"{row.skor_topsis:.3f}" in html
    for k, v in CRITERIA.items():
        assert v["desc"] in html and angka(row[k]) in html, k
    assert "bukan keputusan final" in html and "Versi data" in html
    assert "window.print" not in html                      # tanpa ?cetak=1 tidak otomatis mencetak
    assert "window.print" in c.get("/cetak/kecamatan/kebon-jeruk?cetak=1").get_data(as_text=True)


@pytest.mark.parametrize("slug", ["tidak-ada", "KEBON-JERUK", "kebon_jeruk", "kebon%20jeruk", "..%2Fapp", "a" * 300])
def test_slug_tidak_valid_404(slug):
    assert c.get(f"/cetak/kecamatan/{slug}").status_code == 404
    assert c.get(f"/ekspor/kecamatan/{slug}.pdf").status_code == 404


def test_pdf_kecamatan_cadangan_jika_weasyprint_tidak_ada(monkeypatch):
    monkeypatch.setattr(aplikasi, "render_pdf", lambda html, base: None)
    r = c.get("/ekspor/kecamatan/tebet.pdf")
    assert r.status_code == 302 and r.headers["Location"].endswith("/cetak/kecamatan/tebet?cetak=1")


def test_pdf_kecamatan_header_jika_weasyprint_ada(monkeypatch):
    monkeypatch.setattr(aplikasi, "render_pdf", lambda html, base: b"%PDF-palsu")
    r = c.get("/ekspor/kecamatan/tebet.pdf")
    assert r.status_code == 200 and r.mimetype == "application/pdf"
    assert "profil-tebet.pdf" in r.headers["Content-Disposition"] and r.data.startswith(b"%PDF")


BOBOT_PAKAR = [10, 15, 15, 10, 10, 20, 10, 10]


def test_pdf_simulasi_json_dan_form(monkeypatch):
    monkeypatch.setattr(aplikasi, "render_pdf", lambda html, base: html.encode())   # tangkap HTML yang akan dijadikan PDF
    for kirim in (lambda: c.post("/ekspor/simulasi.pdf", json={"bobot": BOBOT_PAKAR, "preset": "pakar"}),
                  lambda: c.post("/ekspor/simulasi.pdf", data={"payload": json.dumps({"bobot": BOBOT_PAKAR, "preset": "pakar"})})):
        r = kirim()
        assert r.status_code == 200 and r.mimetype == "application/pdf"
        html = r.get_data(as_text=True)
        assert "Simulasi Bobot: Pakar" in html and "20.0%" in html
        assert html.count("<tr>") >= 42                      # 42 kecamatan + judul kolom


def test_pdf_simulasi_cadangan_html(monkeypatch):
    monkeypatch.setattr(aplikasi, "render_pdf", lambda html, base: None)
    r = c.post("/ekspor/simulasi.pdf", json={"bobot": BOBOT_PAKAR, "preset": "pakar"})
    assert r.status_code == 200 and r.mimetype == "text/html" and "window.print" in r.get_data(as_text=True)


def test_pdf_simulasi_payload_tidak_valid():
    for kirim in (lambda: c.post("/ekspor/simulasi.pdf", json={"bobot": [1] * 7}),
                  lambda: c.post("/ekspor/simulasi.pdf", json={"bobot": [0] * 8}),
                  lambda: c.post("/ekspor/simulasi.pdf", json={"bobot": BOBOT_PAKAR, "preset": "aneh"}),
                  lambda: c.post("/ekspor/simulasi.pdf", data={"payload": "bukan json"}),
                  lambda: c.post("/ekspor/simulasi.pdf")):
        assert kirim().status_code == 400


def test_simulasi_get_tidak_diizinkan():
    assert c.get("/ekspor/simulasi.pdf").status_code == 405


def test_weasyprint_asli():
    """Hanya berjalan di mesin yang pustaka sistem WeasyPrint-nya lengkap (mis. PythonAnywhere)."""
    r = c.get("/ekspor/kecamatan/kebon-jeruk.pdf")
    if r.status_code == 302:
        pytest.skip("WeasyPrint/pustaka sistem tidak tersedia di mesin ini")
    assert r.status_code == 200 and r.data.startswith(b"%PDF")
    r2 = c.post("/ekspor/simulasi.pdf", json={"bobot": BOBOT_PAKAR, "preset": "pakar"})
    assert r2.status_code == 200 and r2.data.startswith(b"%PDF")
