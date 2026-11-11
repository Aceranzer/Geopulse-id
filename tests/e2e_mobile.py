"""Uji tampilan ponsel (375x667) di browser sungguhan (Playwright + Microsoft Edge).

Tidak ikut `pytest`. Butuh: pip install playwright (Edge harus terpasang).
Jalankan dari akar repo:  python tests/e2e_mobile.py   (tangkapan layar disimpan di folder sementara)
"""
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SHOT = Path(tempfile.mkdtemp(prefix="geopulse_mobile_"))
URL = "http://127.0.0.1:5058"
LEBAR, TINGGI = 375, 667
HALAMAN = ["/", "/simulasi", "/komparasi?a=CENGKARENG&b=TANAH%20ABANG", "/klaster", "/metodologi"]

srv = subprocess.Popen([sys.executable, "-c", "import app; app.app.run(port=5058)"], cwd=ROOT,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(60):
    try:
        urllib.request.urlopen(URL + "/api/geojson", timeout=1); break
    except Exception:
        time.sleep(0.5)

hasil = []


def cek(nama, kondisi, rinci=""):
    hasil.append((nama, bool(kondisi)))
    print(("LULUS " if kondisi else "GAGAL ") + nama, rinci)


def tunggu(pg, url):
    pg.goto(URL + url)
    pg.wait_for_load_state("networkidle")
    pg.wait_for_timeout(600)


def lebar_halaman(pg):
    return pg.evaluate("document.documentElement.scrollWidth")


try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        ctx = b.new_context(viewport={"width": LEBAR, "height": TINGGI}, device_scale_factor=2, is_mobile=True, has_touch=True)
        pg = ctx.new_page()
        galat_js = []
        pg.on("pageerror", lambda e: galat_js.append(str(e)))

        for mode in ["bawaan", "aktif"]:
            if mode == "aktif":
                pg.goto(URL + "/simulasi"); pg.wait_for_selector("#tabel tbody tr")
                pg.click('.preset[data-mode="pakar"]'); pg.wait_for_function("document.querySelector('#ringkasan').innerText.includes('Pakar')")
                pg.click("#btn-terapkan")
            for i, url in enumerate(HALAMAN):
                tunggu(pg, url)
                nama = url.split("?")[0].strip("/") or "dashboard"
                w = lebar_halaman(pg)
                cek(f"[{mode}] {nama}: tidak ada gulir horizontal halaman ({w}px <= {LEBAR}px)", w <= LEBAR, "" if w <= LEBAR else "MELUBER")
                pg.screenshot(path=str(SHOT / f"{mode}_{nama}.png"), full_page=True)

        # --- detail per halaman (bobot aktif sedang menyala)
        tunggu(pg, "/")
        pg.wait_for_selector("#tabel tbody tr")
        cek("banner aktif: tombol Reset di baris bawah teks",
            pg.evaluate("document.getElementById('banner-reset').getBoundingClientRect().top >= document.querySelector('#banner-bobot span').getBoundingClientRect().bottom - 1"))
        tinggi_peta = pg.evaluate("document.getElementById('peta').getBoundingClientRect().height")
        cek(f"peta tingginya >= 300px ({tinggi_peta:.0f}px)", tinggi_peta >= 300)
        kol2 = pg.evaluate("getComputedStyle(document.querySelector('#tabel tbody tr td:nth-child(2)')).position")
        cek("tabel: kolom Kecamatan menempel (sticky)", kol2 == "sticky", kol2)
        bisa_gulir = pg.evaluate("(() => { const w = document.getElementById('tabel').parentElement; return w.scrollWidth > w.clientWidth; })()")
        cek("tabel: bisa digulir horizontal di dalam kartu", bisa_gulir)
        pg.evaluate("document.querySelector('#tabel').parentElement.scrollLeft = 300")
        pos = pg.evaluate("(() => { const t = document.querySelector('#tabel tbody tr td:nth-child(2)').getBoundingClientRect(); return [t.left, t.right]; })()")
        cek("tabel: setelah digulir, nama kecamatan tetap terlihat di kiri", pos[0] >= -1 and pos[0] < 120, str([round(x) for x in pos]))
        pg.locator("#top3 .rank-row").first.click(); pg.wait_for_selector("#detail[open]")
        kotak = pg.evaluate("(() => { const r = document.getElementById('detail').getBoundingClientRect(); return [r.width, r.height]; })()")
        cek("detail kecamatan: layar penuh di ponsel", kotak[0] >= LEBAR - 1 and kotak[1] >= TINGGI - 1, str([round(x) for x in kotak]))
        pg.screenshot(path=str(SHOT / "detail.png"))
        pg.click("#detail-tutup")

        tunggu(pg, "/simulasi")
        pg.wait_for_selector("#sliders .slider-row")
        atas = pg.evaluate("(() => { const r = document.querySelector('.slider-row'); return r.querySelector('label').getBoundingClientRect().bottom <= r.querySelector('input').getBoundingClientRect().top + 1; })()")
        cek("simulasi: label di atas slider", atas)
        cek("simulasi: tombol Terapkan terlihat", pg.locator("#btn-terapkan").is_visible())
        pg.evaluate("document.querySelector('#tabel').parentElement.scrollLeft = 300")
        k1 = pg.evaluate("document.querySelector('#tabel tbody tr td:nth-child(1)').getBoundingClientRect().left")
        cek("simulasi: kolom Kecamatan menempel setelah digulir", -1 <= k1 < 40, f"{k1:.0f}")

        tunggu(pg, "/metodologi")
        cek("metodologi: kolom bobot aktif terisi 8 baris",
            pg.evaluate("[...document.querySelectorAll('td.kol-aktif')].filter(e => !e.hidden && /%$/.test(e.textContent)).length") == 8)
        cek("metodologi: tabel arti kriteria 8 baris + alur kerja",
            pg.evaluate("[...document.querySelectorAll('h2')].find(h => h.textContent.includes('Arti tiap kriteria')).nextElementSibling.nextElementSibling.querySelectorAll('tbody tr').length") == 8
            and pg.locator(".alur span").count() == 6)

        cek("tidak ada galat JavaScript", not galat_js, "; ".join(galat_js)[:200])
        b.close()
finally:
    srv.terminate()

gagal = [n for n, ok in hasil if not ok]
print(f"\n{len(hasil) - len(gagal)}/{len(hasil)} pemeriksaan lulus | tangkapan layar: {SHOT}")
sys.exit(1 if gagal else 0)
