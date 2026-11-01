# PLAN: Website Geopulse-ID (Flask) — revisi 2

Dokumen ini menggantikan plan sebelumnya. Baca seluruhnya sebelum lanjut. Fase 0–4 sudah selesai di branch `phase-2-ringkasan`, `phase-3-klaster-komparasi`, `phase-4-simulasi`. Plan ini mencatat **state saat ini**, **keputusan arsitektur terbaru**, dan **fase delta sisa**.

## 1. Target pengguna (direvisi)

**Primer (Gform User Evaluation 5%):** staff BPBD role-play. Ini mengubah tone & prioritas:
- Rekomendasi harus **konkret & actionable** ("tambah 2 EWS di titik X"), bukan deskriptif
- Metadata data (tahun, sumber) harus **visible di tiap halaman**, bukan terkubur di Metodologi
- Framing bahasa: "alat bantu analisis" bukan "showcase"
- PDF export penting (bawa ke rapat)

**Sekunder:** dosen & asdos (40% Aplikasi + 10% Ethics + 10% Explainability), reviewer PKM (first impression), mahasiswa/peneliti (replikasi).

**Risiko etika:** jangan terlihat sebagai sistem resmi BPBD. Banner tipis "Proyek mahasiswa UKRIDA · Alat bantu, bukan sistem resmi" wajib di tiap halaman.

## 2. Status saat ini (sudah selesai)

| Komponen | File | Status |
|---|---|---|
| Konfigurasi | `config.py`, `requirements.txt`, `.gitignore` | ✅ |
| Pipeline TOPSIS + K-Means + sweep k=2..7 | `src/pipeline.py`, `src/topsis.py`, `src/validate.py` | ✅ |
| CSV hasil + GeoJSON di-commit | `data/topsis_result.csv`, `data/clustered_result.csv`, `data/k_sweep.csv`, `data/kecamatan_poly.geojson` | ✅ |
| API JSON (read-only) | `/api/kecamatan`, `/api/kriteria`, `/api/klaster`, `/api/sweep`, `/api/geojson` | ✅ |
| Halaman Ringkasan (KPI, peta, top 3, tabel 42) | `templates/ringkasan.html`, `static/js/ringkasan.js` | ✅ (perlu banyak revisi) |
| Halaman Klaster | `templates/klaster.html`, `static/js/klaster.js` | ✅ (perlu adaptasi bobot aktif) |
| Halaman Komparasi | `templates/komparasi.html`, `static/js/komparasi.js` | ✅ (perlu adaptasi bobot aktif) |
| Halaman Simulasi (preset + slider + pergeseran) | `templates/simulasi.html`, `static/js/simulasi.js`, `static/js/topsis.js` | ✅ (akan diubah drastis) |
| Tes | `tests/test_app.py`, `tests/test_equivalence.py`, `tests/test_topsis_js.py` | ✅ |

## 3. Keputusan arsitektur (final)

### 3.1 Lima halaman, bukan empat
Pertahankan 4 halaman existing + tambah Metodologi. Alasan: tidak worth merge-restructure untuk kode yang sudah jalan.

Final: Ringkasan (`/`), Simulasi (`/simulasi`), Komparasi (`/komparasi`), Klaster (`/klaster`), Metodologi (`/metodologi`).

### 3.2 Bobot aktif sesi (fitur utama baru)
Simulasi tidak lagi berdiri sendiri — bobot yang diterapkan di Simulasi **mempengaruhi semua halaman lain dalam sesi tab yang sama**.

**Alur:**
1. User di Simulasi: pilih preset / geser slider → klik **"Terapkan ke Dashboard"**
2. Bobot + nama preset disimpan di `sessionStorage` (bukan localStorage — hilang saat tutup tab, mencegah "kebawa bobot" antar sesi)
3. Semua halaman (Ringkasan, Komparasi, Klaster) saat load: cek `sessionStorage` → kalau ada → request pipeline dengan bobot aktif → kalau tidak → request baseline
4. Banner global tipis muncul di bawah nav saat bobot aktif ≠ default:
   > ⓘ Bobot aktif: **Kustom** · klik untuk ubah · [Reset ke bawaan]

   Seluruh banner clickable → `/simulasi`. Tombol Reset `stopPropagation`.
5. Reset menghapus `sessionStorage` dan reload halaman.

**Klaster ikut recompute (Opsi B):**
- Tiap Apply = full pipeline re-run (K-Means + silhouette + sweep k=2..7).
- Nama klaster "Prioritas Tinggi/Waspada/Menengah/Rendah" tetap konsisten karena re-labeling by rata-rata skor TOPSIS.
- `cluster_id` 0..3 tetap urut dari tertinggi — hanya anggotanya yang berubah.
- Latency target: < 2 detik per Apply di PA free. **Caching wajib** (lihat 3.3).

### 3.3 Endpoint pipeline + caching
Satu endpoint utama di `app.py`:

```python
@app.route("/api/pipeline", methods=["POST"])
def api_pipeline():
    bobot = request.json.get("bobot")  # list 8 angka
    # validasi: panjang 8, semua >= 0, total > 0, normalisasi ke sum=1
    # hash bobot → kalau sama dengan cache terakhir, return cache
    # kalau tidak: panggil compute_topsis(master, bobot) + compute_clusters()
    # return {topsis: [...], klaster: {...}, sweep: [...], metrics: {...}}
```

**Caching:** module-level dict `_CACHE: dict[str, dict]` dengan key = SHA1 bobot. Max 20 entry (LRU). Baseline bobot entropi di-prefill saat app start.

Endpoint lama tetap:
- `GET /api/kecamatan`, `GET /api/klaster`, `GET /api/sweep` → return baseline (shortcut untuk halaman tanpa bobot aktif, lebih cepat tanpa POST)
- `GET /api/kriteria` → return bobot entropi/sama/pakar + metadata kriteria
- `GET /api/geojson` → poligon

Hapus `POST /api/simulasi` dari plan lama — digantikan `POST /api/pipeline`.

### 3.4 Simulasi di server, bukan JS
Hapus `static/js/topsis.js` + `tests/test_topsis_js.py`. Rewrite `simulasi.js`:
- Debounce 400 ms saat slider digeser → auto preview tabel pergeseran peringkat di halaman Simulasi saja
- Tombol "Terapkan ke Dashboard" terpisah — baru menyimpan ke sessionStorage + feedback "Diterapkan. Buka Dashboard untuk melihat efek."
- Tabel pergeseran peringkat tetap di halaman Simulasi (tampilan "sebelum vs sesudah")

Tes baru: `POST /api/pipeline` dengan bobot entropi harus menghasilkan skor + rank + cluster_id identik dengan baseline CSV.

## 4. Yang perlu DIUBAH dari kondisi sekarang

### 4.1 `base.html` — framing + banner + metadata
- **Hero/branding:** judul "Geopulse-ID" + tagline di bawahnya: *"Alat bantu analisis prioritas mitigasi banjir — 42 kecamatan DKI Jakarta"*
- **Disclaimer banner tipis** (kuning muda) persisten di bawah nav di SEMUA halaman:
  > ⚠️ Proyek mahasiswa UKRIDA (SPK + Data Mining 2026). Alat bantu, bukan sistem resmi BPBD DKI Jakarta.
- **Banner bobot aktif** (biru muda) di bawah disclaimer, muncul kondisional (lihat 3.2).
- **Hapus** tombol "Print Document A4" di nav (baris 19). Pengguna pakai Ctrl+P langsung.
- **Footer** diperluas: sumber data (BPBD DKI Jakarta, Satu Data Jakarta), rentang tahun data (2013–2024), link Github repo, logo/nama tim UKRIDA.

### 4.2 Ringkasan — hero, KPI, peta, panel detail
- **Judul halaman:** "Dashboard Prioritas Mitigasi" (ganti dari "Ringkasan Eksekutif")
- **1 paragraf kecil di atas KPI:** "Peringkat 42 kecamatan DKI Jakarta berdasarkan 8 kriteria risiko banjir, menggunakan metode TOPSIS + K-Means. Peringkat di bawah mengikuti bobot aktif (lihat banner atas kalau non-default)."
- **KPI ke-3 "Estimasi Jiwa Terdampak" → ganti** jadi "Rata-rata Kejadian/Tahun" = `df.kejadian_per_tahun.mean()` dari 42 kecamatan. KPI jiwa terdampak menyesatkan karena double-counting.
- **Peta hillshade** (3 layer):
  - Basemap CartoDB Positron: `https://{s}.basemaps.cartodb.com/light_all/{z}/{x}/{y}.png`
  - Hillshade ESRI (opacity 0.45): `https://services.arcgisonline.com/arcgis/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}`
  - Choropleth (fillOpacity 0.60, turunkan dari 0.85)
  - `L.control.layers` 2 overlay toggle: "Topografi (hillshade)", "Klaster prioritas"
  - Legenda topografi kanan bawah: gradient abu-abu + "Dataran rendah ← → Dataran tinggi"
  - Atribusi: "© OpenStreetMap, © CartoDB, Hillshade: Esri"
- **Panel Detail Kecamatan** — klik baris tabel atau polygon peta → modal/sidebar:
  - Header: nama, kota, rank "#N dari 42"
  - 8 kriteria dengan nilai asli + satuan
  - Skor TOPSIS + pill klaster + nama klaster
  - Daftar rekomendasi dari `rekomendasi(cluster_id)` + catatan "butuh validasi tim lapangan"
  - Tombol "Unduh profil (PDF)" → `GET /ekspor/kecamatan/<slug>.pdf`
- **`ringkasan.js` saat load:** cek sessionStorage bobot aktif → kalau ada, POST `/api/pipeline`, kalau tidak GET `/api/kecamatan`. KPI "Prioritas Tinggi" dan isi tabel + top 3 ikut bobot aktif. KPI "Cakupan Analisis" (jumlah kecamatan) tidak berubah.

### 4.3 Simulasi — tombol Apply + alur baru
- Rewrite `simulasi.js`: hapus import `TopsisJS`, panggil `fetch("/api/pipeline", {method:"POST"})` dengan debounce 400 ms untuk preview di halaman Simulasi
- **Tombol "Terapkan ke Dashboard"** di bawah slider, warna primary. Klik → simpan ke sessionStorage, tampilkan toast/pesan "Diterapkan. Buka Dashboard untuk melihat efek pada peta & peringkat."
- Hapus baris "Verifikasi: perhitungan di browser sama dengan topsis_result.csv..." — tidak relevan (perhitungan di server).
- Tabel pergeseran peringkat (sebelum vs sesudah) tetap — ini value proposition halaman.
- Tombol **"Unduh hasil simulasi (PDF)"** muncul setelah bobot berubah dari default → `POST /ekspor/simulasi.pdf`.

### 4.4 Komparasi — adaptasi bobot aktif
- `komparasi.js` ikut baca sessionStorage. Rank & skor TOPSIS di panel ringkas pakai bobot aktif.
- Nilai asli 8 kriteria TIDAK berubah (karakteristik wilayah tetap sama).
- "Prioritas Tindakan" ikut bobot aktif (rekomendasi dari cluster_id baru).

### 4.5 Klaster — adaptasi bobot aktif + penjelasan
- `klaster.js` ikut baca sessionStorage. Daftar anggota klaster, rata-rata kriteria, Elbow + Silhouette semua pakai bobot aktif.
- Tambah catatan di atas kartu: "Klaster di bawah mengikuti bobot aktif. Baseline (bobot entropi): 14 Prioritas Tinggi, 11 Waspada, 7 Menengah, 10 Rendah." (angka harus dari `metrics.json`, jangan hard-code).

### 4.6 Rekomendasi — isi dengan aturan BNPB konkret
`src/recommend.py` saat ini kosong. Isi dengan 4-6 tindakan konkret per klaster, bukan deskriptif. Target staff BPBD role-play: "apa yang bisa saya lakukan dengan ini?"

Contoh struktur minimal:
```python
RULES = {
    0: [  # Prioritas Tinggi
        {"tindakan": "Prioritaskan pemasangan EWS tambahan di kecamatan tanpa alat peringatan dini (n_alat_dini = 0)",
         "prioritas": "tinggi", "sumber": "BNPB Perka 02/2012 Bab III"},
        {"tindakan": "Sosialisasi musim hujan minimal 2x per tahun di tingkat kelurahan",
         "prioritas": "tinggi", "sumber": "BNPB Perka 02/2012"},
        {"tindakan": "Posko evakuasi siap-siaga di kelurahan dengan kepadatan > 15.000 jiwa/km²",
         "prioritas": "tinggi", "sumber": "BNPB Perka 02/2012"},
        {"tindakan": "Perbaikan drainase mikro & peningkatan tinggi tanggul kritis",
         "prioritas": "sedang", "sumber": "Perda DKI Jakarta ..."},
    ],
    1: [ ... ],  # Waspada
    2: [ ... ],  # Menengah
    3: [ ... ],  # Rendah — pemantauan rutin, kesiapan kontinjensi
}
```

Signature baru: `rekomendasi(cluster_id) -> list[dict] | None`.

Di UI (Komparasi + Detail Kecamatan + PDF): tiap rekomendasi tampil dengan pill prioritas + sitasi kecil + catatan di sudut "Rekomendasi awal dari pedoman BNPB publik — butuh validasi tim lapangan sebelum eksekusi."

**Keputusan tim diperlukan:** validasi/revisi aturan konkret di atas. Default isi dari BNPB Perka 02/2012 yang publik.

## 5. Yang BARU harus ditambahkan

### 5.1 `static/css/print.css`
Dibuat di Fase 7. Dimuat di `base.html` dengan `media="print"`. Isi:
- Sembunyikan nav, footer, banner, kontrol interaktif, slider, tombol
- Sembunyikan hillshade tile saat print: `.leaflet-tile-pane img[src*="Hillshade"] { display: none; }`
- Break per `.card.section`
- Warna aman hitam-putih

### 5.2 Halaman Metodologi (`/metodologi`) — BARU
Route baru di `app.py`:
```python
@app.route("/metodologi")
def metodologi():
    metrics = json.load(open(config.METRICS_JSON))
    return render_template("metodologi.html", metrics=metrics, bobot=bobot(), criteria=CRITERIA)
```

Template `templates/metodologi.html` isi:
- **Sumber data** (dengan link ke dataset): BPBD DKI Jakarta (kejadian banjir 2013–2024, alat EWS), Satu Data Jakarta (kepadatan + luas, GeoJSON kecamatan). 6 sumber diperiksa, 4 dipakai, 2 tidak dipakai (meteorologi, faskes/SDA) + alasannya.
- **Alur CRISP-DM** dengan diagram ASCII atau SVG kecil (6 fase).
- **Perbaikan galat data**: jiwa terdampak dibatasi populasi kelurahan, luas 2014, normalisasi nama.
- **Rumus TOPSIS** + tabel bobot entropi (dari `bobot()`). Tampilkan ketiga bobot (entropi/sama/pakar) side-by-side.
- **Interpretasi per kriteria** — tabel 8 baris: nama, tipe (benefit/cost), satuan, deskripsi, contoh kecamatan nilai tinggi, contoh kecamatan nilai rendah. Ini jawab preempt "kenapa X lebih tinggi dari Y?"
- **K-Means + pemilihan k=4** (Elbow, silhouette, dipilih demi keterbacaan).
- **Keterbatasan**: silhouette ~0.35, wajar untuk 42 data.
- **Etika & privasi**: data agregat, tidak memuat data pribadi, hasil adalah alat bantu bukan keputusan tunggal.
- **Reproducibility**: link ke Github repo, cara jalankan ulang pipeline.

Tambahkan ke `NAV` di `app.py`: `("/metodologi", "Metodologi & Data")`.

### 5.3 `data/metrics.json` — BARU
Ubah pipeline agar menulis file ini saat pipeline selesai:
```json
{
  "timestamp": "2026-11-01T...",
  "n_kecamatan": 42,
  "rentang_tahun": "2013–2017, 2019–2020, 2024",
  "weights": {"entropi": [...], "sama": [...], "pakar": [...]},
  "metrics_baseline": {"silhouette": 0.35, "DBI": ..., "CH": ..., "ukuran_klaster": {"0": 14, "1": 11, "2": 7, "3": 10}}
}
```
Dibaca oleh Metodologi + Detail Kecamatan PDF (untuk "versi data").

### 5.4 CLI entry point `src/__main__.py` — BARU
```python
"""python -m src.pipeline [--input data/dki_master.csv] [--output data/]"""
```
Baca master, panggil `run_pipeline`, tulis `topsis_result.csv` + `clustered_result.csv` + `k_sweep.csv` + `metrics.json`. Dipakai dari README untuk update data (lihat 5.7).

### 5.5 Ekspor PDF — 2 endpoint
WeasyPrint. Cek dulu di PA konsol: `python -c "import weasyprint"`. Fallback kalau gagal: route `/cetak/<slug>` dengan `pdf.css`, user Ctrl+P manual.

**`GET /ekspor/kecamatan/<slug>.pdf`** — 1 halaman A4:
- Validasi `slug` dengan regex `^[a-z0-9-]+$`, 404 kalau tidak ada
- Header: "Profil Prioritas Mitigasi — [Nama Kecamatan], [Kota]"
- Metadata: tanggal unduh, versi data (dari `metrics.json`)
- Tabel 8 kriteria: nama, nilai asli, satuan
- Skor TOPSIS + rank + pill klaster + nama klaster
- Rekomendasi (4-6 item dari `recommend.py`) dengan pill prioritas + sitasi
- Footer: "Geopulse-ID · Alat bantu, bukan keputusan final · UKRIDA 2026"

**`POST /ekspor/simulasi.pdf`** — multi-halaman:
- Payload: `{"bobot": [...], "preset": "..."}`
- Header: "Hasil Simulasi Bobot — [nama preset]"
- Blok bobot (8 kriteria + persen) + tanggal + sitasi
- Tabel 42 kecamatan: rank bawaan, rank baru, selisih (↑/↓/−), urut selisih terbesar
- Footer: timestamp + sumber data

Template `templates/pdf/kecamatan.html`, `templates/pdf/simulasi.html` + `static/css/pdf.css` (terpisah dari print.css karena WeasyPrint CSS engine beda).

### 5.6 `requirements.txt`
Tambah `weasyprint`. Kunci versi semua package.

### 5.7 README update
Hapus semua rujukan Streamlit. Tambahkan bagian "Update data":
```markdown
## Update data (developer)
1. Edit file di `data/raw/`
2. Rebuild master: jalankan notebook `01_data.ipynb` (butuh geopandas)
3. Pipeline: `python -m src.pipeline --input data/dki_master.csv --output data/`
4. Cek lokal: `flask run`
5. `git commit -m "Update data: ..." && git push`
6. Di PA: `git pull && touch /var/www/<user>_pythonanywhere_com_wsgi.py`
```
Juga tambah bagian "Arsitektur" (link ke `docs/PLAN.md`) dan "Reproducibility" (link ke `notebook/`).

## 6. Mobile responsive (Fase 9)

Target: layar 375×667 (iPhone SE) harus tetap kebaca.
- Tabel 42 baris × 9 kolom: horizontal scroll + sticky kolom "Kecamatan" di kiri
- Peta tetap tinggi 300 px minimal
- Banner bobot aktif: wrap, tombol Reset di baris bawah
- Panel Detail Kecamatan: full-screen modal di mobile, sidebar di desktop
- Slider Simulasi: label di atas slider, bukan di samping

## 7. Fase delta (sisanya)

| Fase | Pekerjaan | Selesai jika |
|---|---|---|
| **5** | `POST /api/pipeline` + caching · tombol "Terapkan ke Dashboard" · sessionStorage bobot aktif · banner global clickable · semua JS halaman adaptasi bobot aktif · hapus `topsis.js` + `test_topsis_js.py` | POST /api/pipeline bobot entropi = baseline CSV; klik Apply di Simulasi → buka Dashboard → peta & tabel & top-3 pakai bobot baru; banner muncul & Reset berfungsi; latency < 2s per halaman |
| **6** | Framing (hero + tagline + disclaimer + metadata footer) · hapus Print A4 button · peta hillshade + toggle layer · ganti KPI jiwa terdampak → kejadian/tahun · isi `recommend.py` BNPB konkret (4-6/klaster) | Disclaimer muncul semua halaman; hillshade terlihat; KPI baru di Dashboard; rekomendasi muncul di Komparasi + Detail Kecamatan dengan sitasi |
| **7** | `print.css` · halaman `/metodologi` (dengan interpretasi per kriteria) · `data/metrics.json` · CLI `python -m src.pipeline` | Ctrl+P A4 rapi; Metodologi tampil dengan bobot aktif + tabel kriteria; CLI reproduksi semua CSV + metrics.json |
| **8** | Panel Detail Kecamatan (klik baris → modal) · PDF kecamatan · PDF simulasi | Klik baris → detail; dua endpoint PDF menghasilkan file; `/cetak/<slug>` fallback jalan |
| **9** | Mobile pass · deploy ke PA · README update · uji 1 pengguna + Gform | Lulus di 375px; situs jalan di PA; bukti uji tersimpan |

## 8. Aturan yang tidak boleh dilanggar

1. Semua angka dari file data, tidak ada hard-code (termasuk jumlah per klaster — selalu `.value_counts()` atau dari `metrics.json`).
2. Jumlah kecamatan = 42. `n_alat_dini` tetap cost.
3. `cluster_id` 0..3 berurutan dari skor TOPSIS tertinggi; warna: merah tua, jingga, kuning, hijau.
4. Bobot aktif di sessionStorage, bukan Flask session (per-tab, bukan per-user).
5. Rate-limit `/api/pipeline` opsional di PA (misal 10 req/menit per IP) — abaikan dulu di Fase 5, revisit kalau perlu di Fase 9.
6. `SECRET_KEY` dari env, debug off di produksi.
7. Validasi `slug` + bobot di endpoint PDF (regex + bounds).
8. Disclaimer "proyek mahasiswa, bukan sistem resmi BPBD" wajib visible di tiap halaman.
9. Tidak ada data pribadi; hasil adalah pendukung keputusan.

## 9. Keputusan tim yang masih open

- Isi final `RULES` di `recommend.py` (default dari BNPB Perka 02/2012, tim validasi di Fase 6).
- Preset bobot "Pakar" sekarang di `src/pipeline.py:34` — tim konfirmasi angka final.
- Fallback PDF kalau WeasyPrint gagal di PA (`/cetak/<slug>` + Ctrl+P manual).
- Logo/nama tim UKRIDA untuk footer.

## 10. Cara kerja

- Satu fase = satu branch/PR (`phase-5-bobot-aktif`, `phase-6-framing`, dst).
- Setelah tiap fase: jalankan `flask run`, uji manual, sebutkan hasil. Jangan nyatakan selesai tanpa dijalankan.
- `pytest` sebelum push tiap fase.
- Keputusan yang tidak ada di plan → berhenti dan tanya, jangan menebak.
- Fase 5 adalah fase terbesar — bagi jadi beberapa commit kecil di dalam branch.
