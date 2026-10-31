# Geopulse-id

**Pengembangan Sistem Pendukung Keputusan Berbasis Dashboard Analitik dengan Integrasi K-Means Clustering dan TOPSIS untuk Prioritas Mitigasi Banjir di DKI Jakarta**

* **Pipeline Utama:** Data Satu Data Jakarta $\longrightarrow$ Multi-Criteria Decision Making (TOPSIS) $\longrightarrow$ K-Means Clustering $\longrightarrow$ Website Analitik (Flask)
* **Cakupan Wilayah:** 42 Kecamatan daratan DKI Jakarta (Kabupaten Administrasi Kepulauan Seribu dipisahkan).

---

## 📁 Struktur Direktori

```text
Geopulse-id/
├── app.py                         # Website Flask (halaman + API JSON + ekspor PDF)
├── config.py                      # Path data; SECRET_KEY dari environment variable
├── requirements.txt               # Semua kebutuhan (notebook + website)
├── requirements-web.txt           # Kebutuhan minimal website (untuk deploy)
├── data/
│   ├── raw/                       # File mentah Satu Data Jakarta (.xls) & kecamatan.geojson
│   ├── interim/                   # Data antara (diabaikan git; dibuat ulang oleh notebook)
│   ├── dki_master.csv             # Master dataset 42 kecamatan (hasil 01_data.ipynb)
│   ├── topsis_result.csv          # Skor & ranking TOPSIS
│   ├── clustered_result.csv       # Klaster K-Means per kecamatan
│   ├── k_sweep.csv                # Metrik K-Means untuk k=2..7
│   ├── metrics.json               # Bobot, silhouette/DBI/CH, ukuran klaster, waktu hitung
│   └── kecamatan_poly.geojson     # Poligon 42 kecamatan untuk peta website
├── notebook/                      # 01_data, 02_topsis, 03_kmeans, 04_viz
├── src/
│   ├── topsis.py                  # Fungsi TOPSIS & bobot Entropi Shannon
│   ├── pipeline.py                # TOPSIS + K-Means dari tabel master (juga CLI)
│   ├── validate.py                # Aturan validasi data
│   └── recommend.py               # Rekomendasi tindakan per klaster (draf awal)
├── templates/  static/            # Halaman HTML, CSS, JS (Leaflet, Chart.js)
├── tests/                         # pytest
└── docs/                          # DEPLOY.md, UJI_PENGGUNA.md, PANDUAN_PENJELASAN_TOPSIS.md
```

---

## 🚀 Panduan Menjalankan

### 1. Instalasi Dependensi
```bash
python -m venv .venv
.venv\Scriptsctivate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
```
Penting: nama folder `data/raw` huruf kecil semua (sistem Linux membedakan huruf besar/kecil).

### 2. Eksekusi Pipeline Berurutan
1. Jalankan `notebook/01_data.ipynb` untuk memproses data mentah menjadi `data/dki_master.csv`.
2. Jalankan `notebook/02_topsis.ipynb` untuk menghitung skor risiko TOPSIS dan menghasilkan `data/topsis_result.csv`.
3. Jalankan `notebook/03_kmeans.ipynb` untuk mengelompokkan kecamatan ke dalam 4 klaster prioritas mitigasi.
4. Jalankan `notebook/04_viz.ipynb` untuk membuat figur final.

### 3. Menjalankan website
```bash
python app.py            # buka http://127.0.0.1:5000
python -m pytest tests   # jalankan semua tes
```
Halaman: Ringkasan (`/`), Simulasi Bobot (`/simulasi`), Komparasi Wilayah (`/komparasi`), Klaster (`/klaster`), Metodologi & Data (`/metodologi`).
Semua angka dibaca dari file di `data/`. Untuk produksi, atur `SECRET_KEY` sebagai environment variable.

Catatan PDF: ekspor PDF memakai WeasyPrint yang butuh pustaka sistem (Pango/Cairo). Jika tidak tersedia (mis. di Windows), tombol PDF otomatis membuka halaman cetak browser ("Simpan sebagai PDF").

### 4. Update data (developer)
1. Ubah/tambah file di `data/raw/`.
2. Jalankan ulang `notebook/01_data.ipynb` untuk membangun `data/dki_master.csv`.
3. Hitung ulang hasil:
   ```bash
   python -m src.pipeline --input data/dki_master.csv --output data/
   ```
   Data ditolak (dan tidak ada file yang ditulis) bila tidak tepat 42 kecamatan, nama tidak cocok dengan GeoJSON, ada nilai kosong/negatif, atau `jiwa_per_1000` di luar 0–1000.
4. Cek lokal dengan `python app.py` dan `python -m pytest tests`.
5. Commit dan push: `git add data/ && git commit -m "Update data: ..." && git push`.
6. Di server: `git pull`, lalu reload (lihat [docs/DEPLOY.md](docs/DEPLOY.md)).

Catatan: bobot entropi dihitung dari data, sehingga data baru ikut menggeser bobot dan peringkat.

### 5. Deploy
Panduan lengkap PythonAnywhere ada di [docs/DEPLOY.md](docs/DEPLOY.md); skenario uji pengguna di [docs/UJI_PENGGUNA.md](docs/UJI_PENGGUNA.md).

---

## 📐 Metodologi TOPSIS Murni & Pembobotan Entropi

Metode **TOPSIS (*Technique for Order of Preference by Similarity to Ideal Solution*)** digunakan untuk menentukan tingkat urgensi risiko dan prioritas penanganan banjir di 42 kecamatan.

### 1. Landasan Konseptual: *Disaster Risk Framework*
Penentuan kriteria didasarkan pada kerangka baku mitigasi bencana internasional:
$$\text{Risiko Banjir} = \frac{\text{Bahaya (Hazard)} \times \text{Kerentanan (Vulnerability)}}{\text{Kapasitas (Capacity)}}$$

### 2. Daftar Alternatif (42 Kecamatan Daratan DKI Jakarta)
Analisis dilakukan pada **42 alternatif kecamatan** di 5 wilayah kota administrasi (Kepulauan Seribu dipisahkan agar fokus pada dinamika daratan Jakarta):

| Wilayah Kota | Jumlah | Daftar Alternatif Kecamatan |
| :--- | :---: | :--- |
| **Jakarta Barat** | 8 | Cengkareng, Grogol Petamburan, Kali Deres, Kebon Jeruk, Kembangan, Palmerah, Taman Sari, Tambora |
| **Jakarta Pusat** | 8 | Cempaka Putih, Gambir, Johar Baru, Kemayoran, Menteng, Sawah Besar, Senen, Tanah Abang |
| **Jakarta Selatan** | 10 | Cilandak, Jagakarsa, Kebayoran Baru, Kebayoran Lama, Mampang Prapatan, Pancoran, Pasar Minggu, Pesanggrahan, Setia Budi, Tebet |
| **Jakarta Timur** | 10 | Cakung, Cipayung, Ciracas, Duren Sawit, Jatinegara, Kramat Jati, Makasar, Matraman, Pasar Rebo, Pulo Gadung |
| **Jakarta Utara** | 6 | Cilincing, Kelapa Gading, Koja, Pademangan, Penjaringan, Tanjung Priok |

### 3. Penetapan Kriteria & Arah (Benefit vs Cost)
Terdapat **8 kriteria** yang mencakup 3 pilar risiko bencana:

| No | Kode Kriteria | Dimensi | Tipe | Satuan | Alasan & Arah Optimasi |
| :---: | :--- | :---: | :---: | :---: | :--- |
| 1 | `frek_tahun_banjir` | Bahaya | **Benefit** | Proporsi (0–1) | Semakin sering banjir tahunan, semakin tinggi prioritas mitigasi. |
| 2 | `bulan_banjir_per_tahun` | Bahaya | **Benefit** | Bulan/tahun | Semakin banyak bulan basah banjir, semakin darurat. |
| 3 | `kejadian_per_tahun` | Bahaya | **Benefit** | Kejadian/tahun | Frekuensi kejadian tahunan yang tinggi menuntut intervensi. |
| 4 | `tinggi_max_cm` | Bahaya | **Benefit** | cm | Genangan yang tinggi menimbulkan keparahan fisik yang lebih besar. |
| 5 | `lama_hari_mean` | Bahaya | **Benefit** | Hari | Durasi genangan yang lama melumpuhkan aktivitas ekonomi warga. |
| 6 | `jiwa_per_1000` | Bahaya | **Benefit** | Jiwa/1.000 pddk | Dampak korban jiwa/pengungsi per 1.000 warga (urgensi kemanusiaan). |
| 7 | `kepadatan_jiwa_km2` | Kerentanan | **Benefit** | Jiwa/km² | Semakin padat penduduk, semakin banyak jiwa yang terpapar risiko. |
| 8 | `n_alat_dini` | Kapasitas | **Cost** | Unit EWS | Semakin minim alat EWS terpasang, semakin darurat butuh penambahan (Cost). |

### 4. Metode Pembobotan Objektif: Shannon Entropy
Bobot kriteria tidak ditentukan secara subjektif, melainkan dihitung secara objektif menggunakan dispersi informasi alami data:
1. Normalisasi matriks probabilitas: $p_{ij} = \frac{x_{ij}}{\sum_{i=1}^m x_{ij}}$
2. Entropi kriteria ($k = \frac{1}{\ln(m)}$): $e_j = -k \sum_{i=1}^m p_{ij} \ln(p_{ij})$
3. Derajat divergensi informasi: $d_j = 1 - e_j$
4. Bobot ternormalisasi: $w_j = \frac{d_j}{\sum_{j=1}^n d_j}$

*Sebagai pembanding keandalan (analisis sensitivitas), disiapkan juga skenario **Equal Weights** ($w_j = 1/n$) dan **Expert Weights**.*

### 5. Lima Langkah Matematis Algoritma TOPSIS Murni
1. **Normalisasi Vektor ($r_{ij}$):**
   $$r_{ij} = \frac{x_{ij}}{\sqrt{\sum_{k=1}^m x_{kj}^2}}$$
2. **Matriks Ternormalisasi Terbobot ($v_{ij}$):**
   $$v_{ij} = w_j \times r_{ij}$$
3. **Menentukan Solusi Ideal Positif ($A^+$) dan Solusi Ideal Negatif ($A^-$):**
   * Untuk kriteria **Benefit**: $A_j^+ = \max_i(v_{ij}), \quad A_j^- = \min_i(v_{ij})$
   * Untuk kriteria **Cost**: $A_j^+ = \min_i(v_{ij}), \quad A_j^- = \max_i(v_{ij})$
4. **Menghitung Jarak Euclidean ($D_i^+$ dan $D_i^-$):**
   $$D_i^+ = \sqrt{\sum_{j=1}^n (v_{ij} - A_j^+)^2}, \quad D_i^- = \sqrt{\sum_{j=1}^n (v_{ij} - A_j^-)^2}$$
5. **Menghitung Nilai Preferensi / Kedekatan Relatif ($C_i$):**
   $$C_i = \frac{D_i^-}{D_i^+ + D_i^-}$$
   * Rentang nilai $C_i \in [0, 1]$.
   * Semakin mendekati 1, kecamatan tersebut semakin dekat ke skenario bencana terburuk dan paling jauh dari skenario aman $\longrightarrow$ **Prioritas Darurat Tertinggi (Ranking 1)**.

---

## 🏆 Hasil Peringkat Prioritas TOPSIS (Top 10 Kecamatan)

| Rank | Kecamatan | Wilayah Kota | Skor TOPSIS ($C_i$) | Data pendukung |
| :---: | :--- | :--- | :---: | :--- |
| **1** | **Kebon Jeruk** | Jakarta Barat | **0,832** | 16,2 kali/tahun · air maks 160 cm · 0 alat peringatan dini |
| **2** | **Tanjung Priok** | Jakarta Utara | **0,717** | 7,6 kali/tahun · air maks 105 cm · 0 alat peringatan dini |
| **3** | **Tanah Abang** | Jakarta Pusat | **0,707** | 3,1 kali/tahun · air maks 250 cm · 0 alat peringatan dini |
| **4** | **Penjaringan** | Jakarta Utara | **0,693** | 16,5 kali/tahun · air maks 250 cm · 0 alat peringatan dini |
| **5** | **Cilandak** | Jakarta Selatan | **0,685** | 10,9 kali/tahun · air maks 200 cm · 0 alat peringatan dini |
| **6** | **Sawah Besar** | Jakarta Pusat | **0,674** | 1,8 kali/tahun · air maks 70 cm · 0 alat peringatan dini |
| **7** | **Palmerah** | Jakarta Barat | **0,674** | 3,8 kali/tahun · air maks 150 cm · 0 alat peringatan dini |
| **8** | **Cilincing** | Jakarta Utara | **0,666** | 10,1 kali/tahun · air maks 180 cm · 0 alat peringatan dini |
| **9** | **Mampang Prapatan** | Jakarta Selatan | **0,665** | 10,8 kali/tahun · air maks 200 cm · 0 alat peringatan dini |
| **10** | **Pesanggrahan** | Jakarta Selatan | **0,664** | 8,0 kali/tahun · air maks 200 cm · 0 alat peringatan dini |

*(Tabel dihasilkan dari `data/topsis_result.csv` dengan bobot entropi. Kolom `skor_topsis_6kriteria` memuat skema pembanding 6 kriteria: Top 1 Cengkareng, Top 2 Jatinegara.)*

> **Catatan:** bobot entropi memberi bobot terbesar pada `n_alat_dini` (hampir separuh total), sehingga peringkat sangat sensitif terhadap pilihan bobot (lihat halaman Simulasi Bobot). Ini dicatat sebagai keterbatasan di halaman Metodologi.

---

## 📊 K-Means Clustering

* **Fitur Input:** `skor_topsis` (output Stage TOPSIS) dipadukan dengan `jiwa_per_1000` (dampak ke warga) dan `kepadatan_jiwa_km2` (paparan penduduk); log1p + standardisasi (z-score).
* **Jumlah Klaster:** $k = 4$ (Klaster 0: Prioritas Tinggi ... Klaster 3: Rendah), dipilih dari sweep k=2..7 dengan aturan kelayakan (ukuran klaster ≥ 5 dan ≤ 40% data, Spearman klaster-vs-rank ≥ 0,8). Silhouette k=4 (0,354) mendekati k=6 (0,378) sebagai yang tertinggi di antara k yang lolos.
* **Evaluasi Klaster** (angka di bawah dihasilkan `03_kmeans.ipynb`):
  * Silhouette Score: 0,351 · Davies-Bouldin Index: 0,880 · Calinski-Harabasz Index: 27,0
  * Stabilitas ARI (Seed / Bootstrap): 0,91 / 0,74
  * Konsistensi dengan TOPSIS: Spearman(klaster, rank) = 0,90; 10/10 kecamatan top-10 TOPSIS berada di klaster 0
  * ARI vs Ward = 0,61, vs GMM = 0,54 (kesepakatan sedang; kecamatan batas: Grogol Petamburan, Cempaka Putih, Kebayoran Lama, Cakung, Kelapa Gading)

---

## 📚 Referensi

* Ashari et al. (2023), *Elbow, Silhouette, Davies-Bouldin, Calinski-Harabasz, and Rand-Index Evaluation on K-Means for Classifying Flood-Affected Areas in Jakarta*, JAIC 7(1):95–103.
* Hwang, C. L., & Yoon, K. (1981), *Multiple Attribute Decision Making: Methods and Applications*, Springer-Verlag.
* Shannon, C. E. (1948), *A Mathematical Theory of Communication*, Bell System Technical Journal, 27(3), 379–423.
