"""Uji ujung-ke-ujung alur bobot aktif di browser sungguhan (Playwright + Microsoft Edge).

Tidak ikut `pytest` (nama berkas tanpa awalan test_). Butuh: pip install playwright (Edge harus terpasang).
Jalankan dari akar repo:  python tests/e2e_bobot_aktif.py   (tangkapan layar disimpan di folder sementara)
"""
import json
import subprocess
import tempfile
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SHOT = Path(tempfile.mkdtemp(prefix="geopulse_e2e_"))
URL = "http://127.0.0.1:5057"

srv = subprocess.Popen([sys.executable, "-c", "import app; app.app.run(port=5057)"], cwd=ROOT,
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

try:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page(viewport={"width": 1500, "height": 1000})
        galat_js = []
        pg.on("pageerror", lambda e: galat_js.append(str(e)))
        pg.on("console", lambda m: galat_js.append(m.text) if m.type == "error" and "tile" not in m.text.lower() and "Failed to load resource" not in m.text else None)

        # --- baseline
        pg.goto(URL + "/"); pg.wait_for_selector("#tabel tbody tr")
        cek("baseline: banner tersembunyi", pg.locator("#banner-bobot").is_hidden())
        kpi0 = pg.inner_text("#kpi-prioritas"); skor0 = pg.inner_text("#kpi-skor")
        top0 = pg.inner_text("#top3 .rank-row >> nth=0")
        cek("baseline: KPI prioritas = 14", kpi0 == "14", kpi0)

        # --- Simulasi: pilih Pakar, pratinjau, terapkan
        pg.goto(URL + "/simulasi"); pg.wait_for_selector("#tabel tbody tr")
        cek("simulasi: tombol PDF tersembunyi saat bobot bawaan", pg.locator("#form-pdf").is_hidden())
        pg.click('.preset[data-mode="pakar"]')
        pg.wait_for_function("document.querySelector('#ringkasan').innerText.includes('Pakar')")
        cek("simulasi: tombol PDF muncul setelah bobot berubah", pg.locator("#form-pdf").is_visible())
        ringkas = pg.inner_text("#ringkasan")
        cek("simulasi: tabel pergeseran terisi 42 baris", pg.locator("#tabel tbody tr").count() == 42, ringkas)
        pg.click("#btn-terapkan")
        cek("simulasi: toast muncul", pg.locator("#toast").is_visible() and "Diterapkan" in pg.inner_text("#toast"))
        cek("simulasi: banner muncul", pg.locator("#banner-bobot").is_visible() and "Pakar" in pg.inner_text("#banner-bobot"))
        tersimpan = pg.evaluate("sessionStorage.getItem('geopulse_bobot_aktif')")
        cek("sessionStorage berisi bobot Pakar", tersimpan and json.loads(tersimpan)["preset"] == "pakar")
        cek("localStorage kosong (bobot tidak lintas-sesi)", pg.evaluate("localStorage.length") == 0)
        pg.screenshot(path=str(SHOT / "e2e_simulasi.png"), full_page=False)

        # --- Dashboard ikut bobot aktif
        pg.goto(URL + "/"); pg.wait_for_selector("#tabel tbody tr")
        cek("dashboard: banner terlihat", pg.locator("#banner-bobot").is_visible())
        top1 = pg.inner_text("#top3 .rank-row >> nth=0")
        cek("dashboard: top-3 berubah mengikuti bobot", top1 != top0, f"{top0.splitlines()[1][:30]!r} -> {top1.splitlines()[1][:30]!r}")
        kpi1 = pg.inner_text("#kpi-prioritas")
        cek("dashboard: KPI dihitung ulang (klaster baru)", kpi1.isdigit(), f"{kpi0} -> {kpi1}")
        baris1 = pg.inner_text("#tabel tbody tr >> nth=0")
        cek("dashboard: baris pertama tabel = kecamatan top-3 aktif", top1.splitlines()[1].split("·")[0].strip().upper() in baris1.upper())
        pg.screenshot(path=str(SHOT / "e2e_dashboard_aktif.png"))

        # klik poligon peta -> detail (dengan bobot aktif)
        pg.wait_for_selector(".leaflet-interactive")
        pg.locator(".leaflet-interactive").first.click(force=True)
        pg.wait_for_selector("#detail[open]", timeout=5000)
        cek("klik poligon peta membuka panel detail", pg.locator("#detail").is_visible())
        href = pg.get_attribute("#detail-isi a.btn", "href")
        cek("tautan PDF detail membawa bobot aktif", "?w=" in href and "p=pakar" in href, href[:70])
        pg.click("#detail-tutup")

        # klik baris tabel dan top-3 juga membuka detail
        pg.locator("#top3 .rank-row").first.click(); pg.wait_for_selector("#detail[open]")
        cek("klik kartu top-3 membuka detail", True); pg.click("#detail-tutup")

        # --- Klaster & Komparasi ikut bobot aktif
        pg.goto(URL + "/klaster"); pg.wait_for_selector("#kartu .klaster-card")
        cek("klaster: status menyebut bobot aktif", "Pakar" in pg.inner_text("#status-bobot"), pg.inner_text("#status-bobot"))
        cek("klaster: catatan baseline dari metrics.json", "Baseline (bobot entropi): 14 Prioritas Tinggi, 11 Waspada, 7 Menengah, 10 Rendah" in pg.inner_text("main"))
        ukuran = [int(x.split()[0]) for x in pg.locator(".klaster-card .n").all_inner_texts()]
        cek("klaster: 4 kartu, total 42", len(ukuran) == 4 and sum(ukuran) == 42, str(ukuran))
        cek("klaster: grafik sweep digambar", pg.locator("#elbow").is_visible())

        pg.goto(URL + "/komparasi?a=CENGKARENG&b=TANAH%20ABANG"); pg.wait_for_selector("#ringkas .card")
        teks = pg.inner_text("#ringkas")
        cek("komparasi: peringkat Cengkareng mengikuti bobot aktif (bukan #40)", "#40" not in teks.split("TANAH")[0], teks.replace("\n", " ")[:80])
        pg.screenshot(path=str(SHOT / "e2e_komparasi_aktif.png"), full_page=True)

        # --- Reset lewat banner
        pg.click("#banner-reset"); pg.wait_for_load_state("load")
        pg.wait_for_selector("#ringkas .card")
        cek("reset: tetap di halaman (tidak pindah ke /simulasi)", pg.url.endswith("/komparasi?a=CENGKARENG&b=TANAH%20ABANG") or "/komparasi" in pg.url, pg.url[-40:])
        cek("reset: banner hilang & storage kosong", pg.locator("#banner-bobot").is_hidden() and pg.evaluate("sessionStorage.length") == 0)
        cek("reset: Cengkareng kembali #40", "#40" in pg.inner_text("#ringkas"))

        # --- klik banner membuka Simulasi
        pg.goto(URL + "/simulasi"); pg.wait_for_selector("#tabel tbody tr")
        pg.click('.preset[data-mode="sama"]'); pg.wait_for_function("document.querySelector('#ringkasan').innerText.includes('Sama rata')")
        pg.click("#btn-terapkan"); pg.goto(URL + "/klaster"); pg.wait_for_selector("#kartu .klaster-card")
        pg.click("#banner-bobot .container span")
        pg.wait_for_url("**/simulasi")
        cek("klik banner membuka halaman Simulasi", pg.url.endswith("/simulasi"))
        pg.wait_for_selector("#tabel tbody tr")
        cek("simulasi memulihkan bobot aktif (Sama rata) saat dibuka", "Sama rata" in pg.inner_text("#ringkasan") and "aktif" in pg.get_attribute('.preset[data-mode="sama"]', "class"))

        # --- terapkan Entropi = reset
        pg.click('.preset[data-mode="entropi"]'); pg.wait_for_function("document.querySelector('#ringkasan').innerText.includes('Entropi')")
        pg.click("#btn-terapkan")
        cek("menerapkan Entropi (bawaan) menghapus bobot aktif", pg.evaluate("sessionStorage.length") == 0 and pg.locator("#banner-bobot").is_hidden())

        # --- slider kustom + debounce: banyak input cepat -> satu hasil konsisten
        pg.click('.preset[data-mode="kustom"]'); pg.wait_for_selector("#s0:not([disabled])")
        pg.locator("#s5").fill("90"); pg.locator("#s5").fill("95")
        pg.wait_for_function("document.querySelector('#ringkasan').innerText.includes('Kustom')", timeout=15000)
        cek("slider kustom: pratinjau terhitung", "Kustom" in pg.inner_text("#ringkasan"))
        cek("slider kustom: persen berjumlah 100", abs(sum(float(x[:-1]) for x in pg.locator("[id^=p]").all_inner_texts() if x.endswith('%')) - 100) < 0.6)

        cek("tidak ada galat JavaScript", not galat_js, "; ".join(galat_js)[:200])
        b.close()
finally:
    srv.terminate()

gagal = [n for n, ok in hasil if not ok]
print(f"\n{len(hasil) - len(gagal)}/{len(hasil)} pemeriksaan lulus")
sys.exit(1 if gagal else 0)
