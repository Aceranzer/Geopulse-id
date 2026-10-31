# PLAN: Website Geopulse-ID (Flask) — revisi

Dokumen ini menggantikan plan lama. Baca seluruhnya sebelum lanjut. Fase 0–4 sudah dikerjakan di branch `phase-2-ringkasan`, `phase-3-klaster-komparasi`, `phase-4-simulasi` — plan ini mencatat apa yang **sudah jalan**, apa yang **harus diubah**, dan apa yang **masih kurang**.

## 1. Status saat ini (sudah selesai)

| Komponen | File | Status |
|---|---|---|
| Konfigurasi | `config.py`, `requirements.txt`, `.gitignore` | ✅ |
| Pipeline TOPSIS + K-Means + sweep k=2..7 | `src/pipeline.py`, `src/topsis.py`, `src/validate.py` | ✅ |
| CSV hasil + GeoJSON di-commit | `data/topsis_result.csv`, `data/clustered_result.csv`, `data/k_sweep.csv`, `data/kecamatan_poly.geojson` | ✅ |
| API JSON | `/api/kecamatan`, `/api/kriteria`, `/api/klaster`, `/api/sweep`, `/api/geojson` | ✅ |
| Halaman Ringkasan (KPI, peta, top 3, tabel 42) | `templates/ringkasan.html`, `static/js/ringkasan.js` | ✅ (perlu revisi, lihat bagian 3) |
| Halaman Klaster (4 kartu + Elbow/Silhouette + sweep) | `templates/klaster.html`, `static/js/klaster.js` | ✅ |
| Halaman Komparasi (A vs B, chart, tabel asli, tindakan) | `templates/komparasi.html`, `static/js/komparasi.js` | ✅ |
| Halaman Simulasi (preset + slider + pergeseran peringkat) | `templates/simulasi.html`, `static/js/simulasi.js`, `static/js/topsis.js` | ✅ (perlu diubah ke server-side, lihat bagian 3) |
| Tes | `tests/test_app.py`, `tests/test_equivalence.py`, `tests/test_topsis_js.py` | ✅ |

## 2. Keputusan struktur (direvisi berdasarkan kondisi riil)

Plan sebelumnya mengusulkan menggabungkan jadi 4 halaman (Dashboard, Jelajah Data, What-If, Metodologi). **Keputusan sekarang: pertahankan 4 halaman yang sudah dibangun, tambahkan Metodologi jadi halaman ke-5.** Alasan:
- 4 halaman existing sudah jalan dan diuji — menggabungkan Simulasi + Komparasi ke "What-If" dan Ringkasan + Klaster ke "Jelajah" = pekerjaan ulang tanpa manfaat fungsional.
- Mahasiswa lebih mudah menjelaskan 5 halaman yang masing-masing punya satu tujuan saat presentasi.
- Ekspor PDF tetap kontekstual, bukan menu nav global.

Final 5 halaman:
1. **Ringkasan** (`/`) — KPI, peta, top 3, tabel 42
2. **Simulasi** (`/simulasi`) — preset bobot + pergeseran peringkat
3. **Komparasi** (`/komparasi`) — A vs B
4. **Klaster** (`/klaster`) — 4 kartu + Elbow/Silhouette
5. **Metodologi** (`/metodologi`) — teks + bobot aktif + sumber data (BARU)

## 3. Yang perlu DIUBAH dari kondisi sekarang

### 3.1 Simulasi: pindahkan perhitungan ke server
Saat ini `simulasi.js` + `topsis.js` menghitung TOPSIS di browser. Pindahkan ke server untuk satu sumber kebenaran dengan pipeline.

- Tambah endpoint `POST /api/simulasi` di `app.py`:
  - Payload: `{"bobot": [8 angka, total ~1.0], "preset": "entropi"|"sama"|"pakar"|"kustom"}`
  - Panggil `src.topsis.topsis(X, bobot, CRIT_TYPES)`, hitung rank, kembalikan `[{kecamatan, wilayah, rank_baru, skor_baru, rank_bawaan, delta}, ...]`
- Rewrite `simulasi.js`: hilangkan import `TopsisJS`, ganti `topsis(X, w, types)` dengan `fetch("/api/simulasi", {method: "POST", body: JSON.stringify({bobot})})`. Debounce 300 ms saat slider digeser.
- **Hapus** `static/js/topsis.js` dan `tests/test_topsis_js.py` (tidak dibutuhkan lagi).
- Tes kesetaraan `test_equivalence.py` tetap. Tambah tes baru: `POST /api/simulasi` dengan bobot entropi harus menghasilkan rank identik dengan `topsis_result.csv`.
- Hapus baris "Verifikasi: perhitungan di browser sama dengan topsis_result.csv..." — tidak relevan lagi karena perhitungan di server.

### 3.2 Peta Ringkasan: tambahkan hillshade + toggle layer
Saat ini `ringkasan.js` hanya menggambar choropleth. Tambah 2 layer dan kontrol:

- Basemap CartoDB Positron: `https://{s}.basemaps.cartodb.com/light_all/{z}/{x}/{y}.png`
- Hillshade ESRI: `https://services.arcgisonline.com/arcgis/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}`, `opacity: 0.45`
- Urutan: basemap → hillshade → choropleth
- `fillOpacity` choropleth: ubah dari 0.85 ke 0.60 agar hillshade terlihat
- Center `[-6.2088, 106.8456]`, zoom 10 (ganti `fitBounds` default)
- `L.control.layers` dengan dua overlay toggle: "Topografi (hillshade)", "Klaster prioritas", keduanya aktif
- Legenda topografi di kanan bawah: gradient abu-abu + teks "Dataran rendah ← → Dataran tinggi"
- Atribusi: "© OpenStreetMap, © CartoDB, Hillshade: Esri"

### 3.3 KPI "Estimasi Jiwa Terdampak" → ganti
"Jiwa terdampak per tahun" dari penjumlahan kejadian menyesatkan karena orang sama bisa terhitung di beberapa kejadian. Ganti kartu KPI ke-3 di `ringkasan.html` jadi salah satu:
- **Opsi A** (direkomendasikan): "Rata-rata Kejadian/Tahun" — `df.kejadian_per_tahun.mean()` dari 42 kecamatan
- **Opsi B**: "Kecamatan Prioritas Tinggi" — `(df.cluster_id == 0).sum()` tapi ini duplikat kartu ke-2
Pilih Opsi A.

### 3.4 Nav header: hapus tombol "Print A4"
Di `base.html` baris 19, hapus `<button class="btn" type="button" onclick="window.print()">Print Document A4</button>`. Pengguna pakai Ctrl+P langsung dari browser; `print.css` yang menanganinya (lihat 4.1).

### 3.5 Rekomendasi: isi dengan aturan BNPB publik
`src/recommend.py` saat ini kosong (`RULES = {}`), menampilkan "belum ditetapkan". Ganti dengan aturan dasar dari pedoman BNPB publik (Perka BNPB 02/2012 tentang Pedoman Umum Pengkajian Risiko Bencana atau yang relevan). Struktur:

```python
RULES = {
    0: [  # Prioritas Tinggi
        {"tindakan": "Pemasangan Early Warning System tambahan dan sosialisasi evakuasi rutin", "prioritas": "tinggi", "sumber": "BNPB Perka 02/2012"},
        {"tindakan": "Perbaikan drainase mikro dan pembangunan tanggul kritis", "prioritas": "tinggi", "sumber": "..."},
        # ...
    ],
    1: [...],  # Waspada
    2: [...],  # Menengah
    3: [...],  # Rendah
}
```

Signature baru: `rekomendasi(cluster_id) -> list[dict] | None`. Di template Komparasi, tampilkan juga catatan "Rekomendasi awal dari pedoman BNPB — butuh validasi tim lapangan sebelum eksekusi" di sudut panel.

## 4. Yang BARU harus ditambahkan

### 4.1 `static/css/print.css` + `@media print`
Dibuat di Fase 5. Dimuat di `base.html`:
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/print.css') }}" media="print">
```
Isi: sembunyikan nav/footer/kontrol, break per section, warna aman untuk hitam-putih, sembunyikan hillshade tile (`.leaflet-tile-pane img[src*="Hillshade"] { display: none; }`) agar peta cetak bersih.

### 4.2 Halaman Metodologi (`/metodologi`) — BARU
Route di `app.py`:
```python
@app.route("/metodologi")
def metodologi():
    with open(config.METRICS_JSON) as f:
        metrics = json.load(f)
    return render_template("metodologi.html", metrics=metrics, bobot=bobot())
```
Template `templates/metodologi.html`: teks statis + angka dari file.
Isi:
- Sumber data: 6 sumber diperiksa, 4 dipakai (kepadatan + luas, kejadian banjir, alat EWS, GeoJSON), 2 tidak dipakai (meteorologi, faskes/SDA) + alasannya.
- Alur CRISP-DM.
- Perbaikan galat data (jiwa terdampak dibatasi populasi kelurahan, luas 2014, normalisasi nama).
- Rumus TOPSIS + bobot entropi (tampilkan bobot aktif dari `bobot()`).
- K-Means + pemilihan k=4 (Elbow, silhouette, dipilih demi keterbacaan).
- Keterbatasan (silhouette ~0.35, wajar untuk 42 data).
- Etika & privasi: data agregat, tidak memuat data pribadi, hasil adalah alat bantu bukan keputusan tunggal.
- Catatan: "Rekomendasi dari sistem adalah panduan awal berbasis pedoman BNPB publik; keputusan final tetap pada BPBD."

Tambahkan ke `NAV` di `app.py`: `("/metodologi", "Metodologi & Data")`.

### 4.3 `data/metrics.json` — BARU
Pipeline saat ini menghasilkan dict `info` tapi tidak menulis file. Ubah entry point agar menulis `metrics.json`:
```python
# di src/__main__.py (BARU) atau dalam notebook 03/04
import json
json.dump({"weights": info["weights"], "metrics": info["metrics"]}, open("data/metrics.json", "w"), indent=2, default=lambda x: x.tolist() if hasattr(x, "tolist") else x)
```
Isi minimal: `weights` (entropi/sama/pakar), `metrics` (silhouette, DBI, CH, ukuran_klaster), `timestamp`, `n_kecamatan`.

### 4.4 CLI entry point `src/__main__.py` — BARU
```python
"""python -m src.pipeline --input data/dki_master.csv --output data/"""
import argparse, json, pandas as pd
from pathlib import Path
from src.pipeline import run_pipeline
# argparse, baca master, panggil run_pipeline, tulis topsis_result.csv + clustered_result.csv + k_sweep.csv + metrics.json
```
Dipakai dari README untuk update data (lihat 4.6).

### 4.5 Panel Detail Kecamatan + ekspor PDF — BARU
Di Ringkasan, klik baris tabel → panel detail (modal atau sidebar):
- Header: nama, kota, rank "#N dari 42"
- 8 kriteria dengan nilai asli + satuan
- Skor TOPSIS + pill klaster + nama klaster
- Daftar rekomendasi dari `rekomendasi(cluster_id)` + catatan validasi
- Tombol "Unduh profil (PDF)" → `GET /ekspor/kecamatan/<slug>.pdf`

Endpoint PDF di `app.py` (WeasyPrint):
```python
@app.route("/ekspor/kecamatan/<slug>.pdf")
def pdf_kecamatan(slug):
    # validasi slug (hanya a-z, 0-9, dash), cari di CSV, 404 kalau tidak ada
    # render templates/pdf/kecamatan.html, HTML(string=...).write_pdf()
```
Template `templates/pdf/kecamatan.html` + `static/css/pdf.css` terpisah dari `print.css`.
Isi 1 halaman A4: header, metadata (tanggal, versi data dari `metrics.json`), tabel 8 kriteria, skor + rank + klaster, rekomendasi, footer "hasil pendukung keputusan, bukan keputusan final".

Catatan WeasyPrint di PythonAnywhere: butuh `pango`, `cairo`, `gdk-pixbuf`. Cek dulu di konsol PA: `python -c "import weasyprint"`. Kalau gagal, fallback: route `/cetak/kecamatan/<slug>` dengan `pdf.css`, pengguna Ctrl+P manual.

### 4.6 Ekspor hasil simulasi PDF — BARU
Di halaman Simulasi, setelah bobot diubah dan tabel ter-render, tampilkan tombol "Unduh hasil simulasi (PDF)":
- Endpoint: `POST /ekspor/simulasi.pdf`, payload bobot aktif
- Isi: header, blok bobot (8 kriteria + persen) + nama preset, tabel 42 kecamatan (rank bawaan → rank baru → selisih, urut selisih terbesar), footer timestamp.

### 4.7 README update
Tambahkan bagian "Update data":
```markdown
## Update data (developer)

1. Edit file di `data/raw/` (misal tambah alat EWS di `jumlah-alat-peringatan-dini-...xls`).
2. Jalankan ulang notebook `01_data.ipynb` untuk membangun ulang `data/dki_master.csv`.
3. Jalankan pipeline:
   ```bash
   python -m src.pipeline --input data/dki_master.csv --output data/
   ```
4. Cek lokal: `flask run`, buka `http://127.0.0.1:5000/`.
5. Commit dan push:
   ```bash
   git add data/ data/raw/
   git commit -m "Update data: <ringkasan perubahan>"
   git push
   ```
6. Di PythonAnywhere: `git pull && touch /var/www/<user>_pythonanywhere_com_wsgi.py`.
```
Hapus semua rujukan ke Streamlit kalau masih ada.

### 4.8 `requirements.txt`
Tambah: `weasyprint`. Pastikan versi dikunci.

## 5. Fase delta (sisanya)

| Fase | Pekerjaan | Selesai jika |
|---|---|---|
| **5** | Simulasi server-side (3.1) + hapus `topsis.js`/`test_topsis_js.py` | `POST /api/simulasi` menghasilkan rank identik dengan `topsis_result.csv` untuk bobot entropi; slider di UI berfungsi tanpa `topsis.js` |
| **6** | Peta hillshade (3.2) + ganti KPI jiwa terdampak (3.3) + hapus tombol Print A4 (3.4) + isi `recommend.py` (3.5) | Hillshade terlihat, toggle layer jalan, KPI baru tampil, rekomendasi muncul di Komparasi dengan catatan validasi |
| **7** | `print.css` (4.1) + Halaman Metodologi (4.2) + `metrics.json` (4.3) + CLI entry (4.4) | Ctrl+P menghasilkan A4 rapi dari semua halaman; `/metodologi` jalan dengan bobot aktif tampil; `python -m src.pipeline` menghasilkan semua CSV + `metrics.json` |
| **8** | Detail Kecamatan + PDF kecamatan (4.5) + PDF simulasi (4.6) | Klik baris tabel → panel detail jalan; dua endpoint PDF menghasilkan file yang bisa dibuka |
| **9** | Deploy ke PythonAnywhere + README update (4.7) + uji 1 pengguna + Gform | Situs jalan di PA; orang lain bisa update data mengikuti README; bukti uji tersimpan |

## 6. Hal yang perlu diputuskan tim

- **Isi rekomendasi final per klaster**: default pakai BNPB publik dengan sitasi, tim validasi/revisi di Fase 6.
- **Isi preset bobot "pakar"**: sudah ada di `src/pipeline.py` baris 34 (`W_EXPERT`), tim konfirmasi apakah angka ini final.
- **Fallback PDF**: pakai WeasyPrint atau route `/cetak/<slug>` + Ctrl+P manual jika WeasyPrint gagal di PA.

## 7. Aturan yang tidak boleh dilanggar (ulangan)

1. Semua angka dari file data, tidak ada hard-code (termasuk jumlah per klaster — hitung dari `df.cluster_id.value_counts()`).
2. Jumlah kecamatan = 42. `n_alat_dini` tetap cost (keputusan tim).
3. `cluster_id` 0..3 berurutan dari skor TOPSIS tertinggi, warna: merah tua, jingga, kuning, hijau.
4. `SECRET_KEY` dari env, debug off di produksi.
5. Validasi `slug` di endpoint PDF (regex `^[a-z0-9-]+$`, cek keberadaan di CSV).
6. Tidak ada data pribadi; hasil adalah pendukung keputusan.

## 8. Cara kerja

- Satu fase = satu branch/PR kecil (`phase-5-simulasi-server`, dst).
- Setelah tiap fase, jalankan `flask run` dan sebutkan apa yang dicoba + hasilnya.
- Jalankan `pytest` sebelum push.
- Pesan commit jelas, mahasiswa harus bisa menjelaskan kodenya saat presentasi.
- Keputusan yang tidak ada di sini → berhenti dan tanya, jangan menebak.
