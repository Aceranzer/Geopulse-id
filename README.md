# Geopulse-id

**Pengembangan Sistem Pendukung Keputusan Berbasis Dashboard Analitik dengan Integrasi K-Means Clustering dan TOPSIS untuk Prioritas Mitigasi Banjir di DKI Jakarta**

* **Pipeline Utama:** Data Satu Data Jakarta $\longrightarrow$ Multi-Criteria Decision Making (TOPSIS) $\longrightarrow$ K-Means Clustering $\longrightarrow$ Dashboard Analitik Streamlit
* **Cakupan Wilayah:** 42 Kecamatan daratan DKI Jakarta (Kabupaten Administrasi Kepulauan Seribu dipisahkan).

---

## 📁 Struktur Direktori

```text
GeoPulse-id/
├── Data/
│   ├── Raw/                       # File mentah Satu Data Jakarta (.xls) & kecamatan.geojson
│   ├── interim/                   # Data antara (geojson poligon, titik EWS, clean kelurahan)
│   ├── dki_master.csv             # Master dataset gabungan 42 kecamatan (hasil 01_data.ipynb)
│   └── topsis_result.csv          # Output skor preferensi & ranking TOPSIS (hasil 02_topsis.ipynb)
├── notebook/
│   ├── 01_data.ipynb              # Data understanding, pembersihan, agregasi & EDA
│   ├── 02_topsis.ipynb            # Bobot Entropi Shannon, TOPSIS murni, sensitivitas & peta
│   └── 03_kmeans.ipynb            # Klasterisasi K-Means k=4, evaluasi metrik & profil klaster
├── src/
│   ├── __init__.py
│   └── topsis.py                  # Modul Python mandiri (reusable) fungsi TOPSIS & Entropi
├── app.py                         # Aplikasi Dashboard Streamlit interaktif
└── README.md
```

---

## 🚀 Panduan Menjalankan

### 1. Instalasi Dependensi
```bash
pip install pandas numpy scikit-learn geopandas matplotlib seaborn lxml jupyter ipykernel
```

### 2. Eksekusi Pipeline Berurutan
1. Jalankan `notebook/01_data.ipynb` untuk memproses data mentah menjadi `Data/dki_master.csv`.
2. Jalankan `notebook/02_topsis.ipynb` untuk menghitung skor risiko TOPSIS dan menghasilkan `Data/topsis_result.csv`.
3. Jalankan `notebook/03_kmeans.ipynb` untuk mengelompokkan kecamatan ke dalam 4 klaster prioritas mitigasi.

---

## 📐 Metodologi TOPSIS Murni & Pembobotan Entropi

Metode **TOPSIS (*Technique for Order of Preference by Similarity to Ideal Solution*)** digunakan untuk menentukan tingkat urgensi risiko dan prioritas penanganan banjir di 42 kecamatan.

### 1. Landasan Konseptual: *Disaster Risk Framework*
Penentuan kriteria didasarkan pada kerangka baku mitigasi bencana internasional:
$$\text{Risiko Banjir} = \frac{\text{Bahaya (Hazard)} \times \text{Kerentanan (Vulnerability)}}{\text{Kapasitas (Capacity)}}$$

### 2. Penetapan Kriteria & Arah (Benefit vs Cost)
| Kriteria | Dimensi | Tipe | Alasan & Arah Optimasi |
| :--- | :---: | :---: | :--- |
| `frek_tahun_banjir` | Bahaya | **Benefit** | Semakin sering banjir tahunan, semakin tinggi prioritas mitigasi. |
| `bulan_banjir_per_tahun` | Bahaya | **Benefit** | Semakin banyak bulan basah banjir, semakin darurat. |
| `kejadian_per_tahun` | Bahaya | **Benefit** | Frekuensi kejadian tahunan yang tinggi menuntut intervensi. |
| `tinggi_max_cm` | Bahaya | **Benefit** | Genangan yang tinggi menimbulkan keparahan fisik yang lebih besar. |
| `lama_hari_mean` | Bahaya | **Benefit** | Durasi genangan yang lama melumpuhkan aktivitas ekonomi warga. |
| `jiwa_per_1000` | Bahaya | **Benefit** | Dampak korban jiwa/pengungsi per 1.000 warga (urgensi kemanusiaan). |
| `kepadatan_jiwa_km2` | Kerentanan | **Benefit** | Semakin padat penduduk, semakin banyak jiwa yang terpapar risiko. |
| `n_alat_dini` | Kapasitas | **Cost** | Semakin banyak EWS yang terpasang, wilayah tersebut semakin siap (risiko termitigasi). |

### 3. Metode Pembobotan Objektif: Shannon Entropy
Bobot kriteria tidak ditentukan secara subjektif, melainkan dihitung secara objektif menggunakan dispersi informasi alami data:
1. Normalisasi matriks probabilitas: $p_{ij} = \frac{x_{ij}}{\sum_{i=1}^m x_{ij}}$
2. Entropi kriteria ($k = \frac{1}{\ln(m)}$): $e_j = -k \sum_{i=1}^m p_{ij} \ln(p_{ij})$
3. Derajat divergensi informasi: $d_j = 1 - e_j$
4. Bobot ternormalisasi: $w_j = \frac{d_j}{\sum_{j=1}^n d_j}$

*Sebagai pembanding keandalan (analisis sensitivitas), disiapkan juga skenario **Equal Weights** ($w_j = 1/n$) dan **Expert Weights**.*

### 4. Lima Langkah Matematis Algoritma TOPSIS Murni
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

| Rank | Kecamatan | Wilayah Kota | Skor TOPSIS ($C_i$) | Keterangan Risiko |
| :---: | :--- | :--- | :---: | :--- |
| **1** | **Kebon Jeruk** | Jakarta Barat | **0,661** | Frekuensi kejadian tinggi, belum memiliki EWS mandiri |
| **2** | **Tanah Abang** | Jakarta Pusat | **0,594** | Kawasan padat penduduk, titik genangan berulang, tanpa EWS |
| **3** | **Tanjung Priok** | Jakarta Utara | **0,579** | Rawan rob pesisir pantai utara, kapasitas deteksi awal minim |
| **4** | **Penjaringan** | Jakarta Utara | **0,567** | Muara sungai & genangan rob laut |
| **5** | **Cilandak** | Jakarta Selatan | **0,565** | Lintasan DAS Krukut dan Pesanggrahan |
| **6** | **Pesanggrahan** | Jakarta Selatan | **0,562** | Daerah aliran sungai rawan luapan |
| **7** | **Sawah Besar** | Jakarta Pusat | **0,558** | Kawasan pemukiman padat perkotaan |
| **8** | **Palmerah** | Jakarta Barat | **0,557** | Kepadatan penduduk tinggi & keterbatasan resapan |
| **9** | **Cilincing** | Jakarta Utara | **0,554** | Wilayah pesisir utara terdampak pasang surut air laut |
| **10** | **Mampang Prapatan** | Jakarta Selatan | **0,553** | Daerah aliran Kali Mampang |

*(Catatan: Dalam file `topsis_result.csv` juga disediakan kolom `skor_topsis_6kriteria` berbasis 6 kriteria murni banjir & kepadatan: Top 1 Jatinegara, Top 2 Cengkareng).*

---

## 📊 K-Means Clustering (Tahap Selanjutnya)

* **Fitur Input:** `skor_topsis` (output Stage TOPSIS) dipadukan dengan 3 fitur pendukung (`tinggi_max_cm`, `lama_hari_mean`, `kepadatan_jiwa_km2`).
* **Jumlah Klaster Optimal:** $k = 4$ (Klaster 0: Prioritas Sangat Tinggi / Kritis $\dots$ Klaster 3: Prioritas Rendah).
* **Evaluasi Klaster:**
  * Silhouette Score: 0,339
  * Davies-Bouldin Index: 0,953
  * Calinski-Harabasz Index: 31,4
  * Stabilitas ARI (Seed / Bootstrap): 0,99 / 0,86

---

## 📚 Referensi

* Ashari et al. (2023), *Elbow, Silhouette, Davies-Bouldin, Calinski-Harabasz, and Rand-Index Evaluation on K-Means for Classifying Flood-Affected Areas in Jakarta*, JAIC 7(1):95–103.
* Hwang, C. L., & Yoon, K. (1981), *Multiple Attribute Decision Making: Methods and Applications*, Springer-Verlag.
* Shannon, C. E. (1948), *A Mathematical Theory of Communication*, Bell System Technical Journal, 27(3), 379–423.
