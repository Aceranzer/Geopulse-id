# Geopulse-id

**Pengembangan Sistem Pendukung Keputusan Berbasis Dashboard Analitik dengan Integrasi K-Means Clustering dan TOPSIS untuk Prioritas Mitigasi Banjir di DKI Jakarta**

* **Pipeline Utama:** Data Satu Data Jakarta $\longrightarrow$ Multi-Criteria Decision Making (TOPSIS) $\longrightarrow$ K-Means Clustering $\longrightarrow$ Visualisasi Final $\longrightarrow$ Explainable AI (XAI) $\longrightarrow$ Dashboard Analitik Streamlit *(tahap berikutnya)*
* **Cakupan Wilayah:** 42 Kecamatan daratan DKI Jakarta (Kabupaten Administrasi Kepulauan Seribu dipisahkan).

---

## 📁 Struktur Direktori

```text
GeoPulse-id/
├── Data/
│   ├── Raw/                       # File mentah Satu Data Jakarta (.xls) & kecamatan.geojson
│   ├── interim/                   # Data antara (geojson poligon, titik EWS, clean kelurahan, fitur z-score)
│   ├── figures/
│   │   ├── final/                 # 10 figure siap laporan, 300 DPI (hasil 04_viz & 05_xai)
│   │   └── preview/               # Figure eksploratif (contoh penjelasan per-kecamatan)
│   ├── dki_master.csv             # Master dataset gabungan 42 kecamatan (hasil 01_data.ipynb)
│   ├── topsis_result.csv          # Output skor preferensi & ranking TOPSIS (hasil 02_topsis.ipynb)
│   ├── clustered_result.csv       # Hasil K-Means: cluster_id, cluster_name, silhouette (hasil 03_kmeans.ipynb)
│   ├── xai_global.csv             # Kepentingan global 8 kriteria (nilai Shapley eksak, hasil 05_xai.ipynb)
│   ├── xai_local.csv              # Kontribusi Shapley per kecamatan x kriteria (hasil 05_xai.ipynb)
│   ├── xai_cluster.csv            # Dekomposisi margin penugasan klaster per fitur (hasil 05_xai.ipynb)
│   └── xai_cluster_importance.csv # Kepentingan fitur partisi K-Means (SSB, share, eta2)
├── notebook/
│   ├── 01_data.ipynb              # Data understanding, pembersihan, agregasi & EDA
│   ├── 02_topsis.ipynb            # Bobot Entropi Shannon, TOPSIS murni, sensitivitas & peta
│   ├── 03_kmeans.ipynb            # Klasterisasi K-Means k=4, evaluasi metrik & profil klaster
│   ├── 04_viz.ipynb               # Visualisasi final figure 01–07 (300 DPI, caption Bahasa Indonesia)
│   └── 05_xai.ipynb               # Explainable AI: Shapley eksak TOPSIS & penjelasan klaster
├── src/
│   ├── __init__.py
│   ├── topsis.py                  # Modul Python mandiri (reusable) fungsi TOPSIS & Entropi
│   └── xai.py                     # Modul XAI: Shapley eksak TOPSIS & dekomposisi klaster
└── README.md
```

---

## 🚀 Panduan Menjalankan

### 1. Instalasi Dependensi
```bash
pip install pandas numpy scikit-learn scipy geopandas matplotlib seaborn lxml jupyter ipykernel
```

### 2. Eksekusi Pipeline Berurutan
1. Jalankan `notebook/01_data.ipynb` untuk memproses data mentah menjadi `Data/dki_master.csv`.
2. Jalankan `notebook/02_topsis.ipynb` untuk menghitung skor risiko TOPSIS dan menghasilkan `Data/topsis_result.csv`.
3. Jalankan `notebook/03_kmeans.ipynb` untuk mengelompokkan kecamatan ke dalam 4 klaster prioritas mitigasi dan menghasilkan `Data/clustered_result.csv`.
4. Jalankan `notebook/04_viz.ipynb` untuk membuat figure 01–07 (300 DPI) di `Data/figures/final/`.
5. Jalankan `notebook/05_xai.ipynb` untuk menjelaskan skor TOPSIS dan penugasan klaster, lalu menghasilkan `Data/xai_*.csv` serta figure 08–11.

> Catatan: `04_viz.ipynb` dan `05_xai.ipynb` menghitung ulang skor TOPSIS dengan `src/topsis.py` dan melakukan *assert* bahwa hasilnya identik dengan `topsis_result.csv`, sehingga tabel dan figure dijamin sinkron dengan data. XAI tidak menambah dependensi baru karena nilai Shapley dihitung eksak dari 2⁸ = 256 koalisi.

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

| No | Kode Kriteria | Dimensi | Tipe | Satuan | Bobot Entropi | Alasan & Arah Optimasi |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| 1 | `frek_tahun_banjir` | Bahaya | **Benefit** | Proporsi (0–1) | 0,01 | Semakin sering banjir tahunan, semakin tinggi prioritas mitigasi. |
| 2 | `bulan_banjir_per_tahun` | Bahaya | **Benefit** | Bulan/tahun | 0,08 | Semakin banyak bulan basah banjir, semakin darurat. |
| 3 | `kejadian_per_tahun` | Bahaya | **Benefit** | Kejadian/tahun | 0,10 | Frekuensi kejadian tahunan yang tinggi menuntut intervensi. |
| 4 | `tinggi_max_cm` | Bahaya | **Benefit** | cm | 0,04 | Genangan yang tinggi menimbulkan keparahan fisik yang lebih besar. |
| 5 | `lama_hari_mean` | Bahaya | **Benefit** | Hari | 0,04 | Durasi genangan yang lama melumpuhkan aktivitas ekonomi warga. |
| 6 | `jiwa_per_1000` | Bahaya | **Benefit** | Jiwa/1.000 pddk | 0,22 | Dampak korban jiwa/pengungsi per 1.000 warga (urgensi kemanusiaan). |
| 7 | `kepadatan_jiwa_km2` | Kerentanan | **Benefit** | Jiwa/km² | 0,04 | Semakin padat penduduk, semakin banyak jiwa yang terpapar risiko. |
| 8 | `n_alat_dini` | Kapasitas | **Cost** | Unit EWS | **0,48** | Semakin minim alat EWS terpasang, semakin darurat butuh penambahan (Cost). |

> **Catatan pembobotan.** Bobot entropi di atas dihitung dari sebaran data 42 kecamatan, bukan ditetapkan manual. Karena `n_alat_dini` sangat timpang (32 dari 42 kecamatan bernilai 0, maksimum 2 unit), kriterium ini memperoleh bobot terbesar (0,48) — hampir setengah skor TOPSIS ditentukan ada/tidaknya EWS. Konsekuensinya, seluruh 10 kecamatan teratas adalah kecamatan tanpa EWS, sedangkan 10 kecamatan yang memiliki EWS semuanya berada di peringkat 33–42. Peringkat di antara sesama kecamatan tanpa EWS ditentukan oleh `jiwa_per_1000` (bobot 0,22). Implikasi ini dibahas pada bagian **Catatan & Limitasi**.

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

| Rank | Kecamatan | Wilayah Kota | Skor TOPSIS ($C_i$) | Klaster | Keterangan Risiko |
| :---: | :--- | :--- | :---: | :---: | :--- |
| **1** | **Kebon Jeruk** | Jakarta Barat | **0,832** | Prioritas Tinggi | Frekuensi kejadian tinggi, belum memiliki EWS mandiri |
| **2** | **Tanjung Priok** | Jakarta Utara | **0,717** | Prioritas Tinggi | Rawan rob pesisir pantai utara, kapasitas deteksi awal minim |
| **3** | **Tanah Abang** | Jakarta Pusat | **0,707** | Prioritas Tinggi | Kawasan padat penduduk, titik genangan berulang, tanpa EWS |
| **4** | **Penjaringan** | Jakarta Utara | **0,693** | Prioritas Tinggi | Muara sungai & genangan rob laut |
| **5** | **Cilandak** | Jakarta Selatan | **0,685** | Prioritas Tinggi | Lintasan DAS Krukut dan Pesanggrahan |
| **6** | **Sawah Besar** | Jakarta Pusat | **0,674** | Prioritas Tinggi | Kawasan pemukiman padat perkotaan |
| **7** | **Palmerah** | Jakarta Barat | **0,674** | Prioritas Tinggi | Kepadatan penduduk tinggi & keterbatasan resapan |
| **8** | **Cilincing** | Jakarta Utara | **0,666** | Prioritas Tinggi | Wilayah pesisir utara terdampak pasang surut air laut |
| **9** | **Mampang Prapatan** | Jakarta Selatan | **0,665** | Prioritas Tinggi | Daerah aliran Kali Mampang |
| **10** | **Pesanggrahan** | Jakarta Selatan | **0,664** | Prioritas Tinggi | Daerah aliran sungai rawan luapan |

*(Rentang skor seluruh 42 kecamatan: 0,160–0,832. Kesepuluh kecamatan teratas berada di klaster 0 — konsisten dengan Spearman 0,90 pada tahap K-Means.)*

*(Catatan: dalam `topsis_result.csv` juga tersedia kolom `skor_topsis_6kriteria` berbasis 6 kriteria murni banjir & kepadatan. Pada skema tersebut Top 1 adalah **Cengkareng** (0,869) dan Top 2 **Jatinegara** (0,687) — berbeda dari skema 8 kriteria karena kriteria EWS tidak diikutkan.)*

---

## 📊 K-Means Clustering

* **Fitur Input:** `skor_topsis` (output Stage TOPSIS) dipadukan dengan `jiwa_per_1000` (dampak ke warga) dan `kepadatan_jiwa_km2` (paparan penduduk); log1p + standardisasi (z-score).
* **Jumlah Klaster:** $k = 4$ (Klaster 0: Prioritas Tinggi ... Klaster 3: Rendah), dipilih dari sweep k=2..7 dengan aturan kelayakan (ukuran klaster ≥ 5 dan ≤ 40% data, Spearman klaster-vs-rank ≥ 0,8). K yang lolos: k = 4, 5, 6; silhouette k=4 (0,354) mendekati k=6 (0,378) sebagai yang tertinggi di antara k yang lolos.
* **Evaluasi Klaster** (angka di bawah dihasilkan `03_kmeans.ipynb`):
  * Silhouette Score: 0,351 · Davies-Bouldin Index: 0,880 · Calinski-Harabasz Index: 27,0
  * Stabilitas ARI (Seed / Bootstrap): 0,91 / 0,74
  * Konsistensi dengan TOPSIS: Spearman(klaster, rank) = 0,90; 10/10 kecamatan top-10 TOPSIS berada di klaster 0
  * ARI vs Ward = 0,61, vs GMM = 0,54 (kesepakatan sedang; kecamatan batas: Grogol Petamburan, Cempaka Putih, Kebayoran Lama, Cakung, Kelapa Gading)
  * Tidak ada kecamatan yang bergeser lebih dari 1 tingkat dibanding kuartil peringkat TOPSIS-nya.

### Komposisi Klaster (hasil `clustered_result.csv`)

| Klaster | Nama | n | Rata-rata Skor | Anggota (urut peringkat TOPSIS) |
| :---: | :--- | :---: | :---: | :--- |
| 0 | **Prioritas Tinggi** | 14 | 0,69 | Kebon Jeruk, Tanjung Priok, Tanah Abang, Penjaringan, Cilandak, Sawah Besar, Palmerah, Cilincing, Mampang Prapatan, Pesanggrahan, Ciracas, Kali Deres, Cakung, Pulo Gadung |
| 1 | **Waspada** | 11 | 0,64 | Kelapa Gading, Pasar Rebo, Grogol Petamburan, Jagakarsa, Cipayung, Duren Sawit, Pademangan, Setia Budi, Gambir, Cempaka Putih, Menteng |
| 2 | **Menengah** | 7 | 0,63 | Matraman, Koja, Tambora, Kemayoran, Taman Sari, Johar Baru, Senen |
| 3 | **Rendah** | 10 | 0,41 | Tebet, Kramat Jati, Pancoran, Kembangan, Kebayoran Baru, Pasar Minggu, Kebayoran Lama, Cengkareng, Jatinegara, Makasar |

*(Urutan klaster ditetapkan dari rata-rata `skor_topsis` tertinggi ke terendah. Rentang skor antar-klaster dapat sedikit tumpang tindih karena pengelompokan memakai 3 fitur, bukan skor TOPSIS saja.)*

---

## 📈 Visualisasi Final (`04_viz.ipynb` & `05_xai.ipynb`)

Seluruh figure dihasilkan pada 300 DPI dengan caption Bahasa Indonesia dan tersimpan di `Data/figures/final/`:

| Fig | Bagian | Konten |
| :---: | :--- | :--- |
| 01 | Metode | Peta cluster 42 kecamatan + label peringkat top-5 |
| 03 | Pembobotan | Perbandingan 3 skema bobot (Equal, Entropy, Expert) |
| 04 | Hasil | Peringkat 42 kecamatan berdasarkan skor TOPSIS |
| 05 | Evaluasi | Pemilihan $k$ (inertia, silhouette, DBI, Spearman) |
| 06 | Profil | PCA + centroid klaster (z-score) |
| 07 | Validasi | Sensitivitas bobot (1.000 simulasi) |
| 08 | XAI | Kepentingan global 8 kriteria + kontribusi per klaster |
| 09 | XAI | Sebaran (beeswarm) kontribusi 8 kriteria di 42 kecamatan |
| 10 | XAI | Waterfall lokal Kebon Jeruk (peringkat 1) |
| 11 | XAI | Kepentingan fitur K-Means + dekomposisi margin kecamatan batas |

Notebook ini menghitung ulang skor TOPSIS lewat `src/topsis.py` dan melakukan *assert* bahwa hasilnya identik dengan `topsis_result.csv`, sehingga tidak ada angka yang ditulis manual.

---

## 🔍 Explainable AI (`05_xai.ipynb`)

Tahap ini **tidak mengubah** bobot, skor, atau penugasan klaster. Tujuannya membuka “kotak hitam” agar pembuat kebijakan dapat melihat kriteria dan fitur mana yang menggerakkan keputusan.

### 1. Menjelaskan skor TOPSIS dengan nilai Shapley eksak

TOPSIS diperlakukan sebagai permainan kooperatif dengan 8 kriteria sebagai pemain. Karena hanya ada $2^8 = 256$ koalisi, seluruh nilai Shapley dienumerasi **eksak** — tanpa SHAP/LIME, tanpa sampling, dan tanpa model pengganti. Baseline yang dipakai adalah **profil teraman** sintetis (kriteria *benefit* = nilai minimum, kriteria *cost* = nilai maksimum), yang skor TOPSIS-nya tepat 0. Dengan demikian kontribusi tiap kriteria dapat dibaca sebagai kenaikan skor dari kondisi teraman menuju kondisi aktual, dan berlaku:

$$\sum_{j=1}^{8}\phi_j(x)=C_i(x)$$

Hasil global (rata-rata 42 kecamatan) menunjukkan dominasi yang jauh lebih besar daripada yang terlihat dari bobot saja:

| Kriteria | Bobot Entropi | Rata-rata \|φ\| | Share \|φ\| |
| :--- | :---: | :---: | :---: |
| `n_alat_dini` | 0,478 | **0,510** | **85,3%** |
| `jiwa_per_1000` | 0,221 | 0,047 | 7,9% |
| `kejadian_per_tahun` | 0,098 | 0,015 | 2,6% |
| `bulan_banjir_per_tahun` | 0,079 | 0,012 | 2,0% |
| 4 kriteria lainnya | 0,124 | ≤ 0,006 | ≤ 1,6% |

Dominasi `n_alat_dini` bukan sekadar bobot 0,48: kriteria ini menyumbang **85,3%** dari total pergerakan skor karena perbedaan 0/1/2 unit EWS menggeser skor jauh lebih besar daripada variasi kriteria bahaya. Peringkat kepentingan XAI sangat mirip dengan bobot entropi (Spearman 0,976), tetapi XAI menunjukkan **besaran** dominasinya secara eksplisit. Hasil ini juga stabil terhadap pilihan baseline: peringkat kepentingan dengan baseline profil teraman vs profil rata-rata identik (Spearman 1,000), dan galat efisiensi Shapley ≤ 3×10⁻¹⁶.

Contoh lokal **Kebon Jeruk** (peringkat 1, $C_i = 0{,}832$): `n_alat_dini` +0,565, `jiwa_per_1000` +0,195, `kejadian_per_tahun` +0,038, `bulan_banjir_per_tahun` +0,023, dan sisanya +0,011. Artinya skor tertinggi ditentukan terutama oleh ketiadaan EWS, lalu oleh besarnya penduduk terdampak — bukan oleh kedalaman genangan.

### 2. Menjelaskan penugasan klaster K-Means

Dua ukuran digunakan:

* **Kepentingan fitur partisi (SSB):** `skor_topsis` 38,4% (η² = 0,78), `jiwa_per_1000` 36,7% (η² = 0,75), `kepadatan_jiwa_km2` 24,9% (η² = 0,51). Ketiga fitur berperan nyata; klaster tidak dibentuk oleh skor TOPSIS semata.
* **Dekomposisi margin penugasan:** untuk tiap kecamatan, selisih jarak kuadrat ke centroid klaster sendiri vs klaster pesaing terdekat dipecah per fitur. Kontribusi negatif berarti fitur **menahan** kecamatan di klasternya; positif berarti **mendorong** ke klaster pesaing.

Enam kecamatan dengan silhouette sampel terendah — Kebayoran Lama, Tebet, Cempaka Putih, Kelapa Gading, Cakung, dan Grogol Petamburan — dianalisis pada Figure 11. Kecamatan-kecamatan ini tetap berada di klasternya, tetapi marginnya tipis sehingga paling sensitif bila data atau jumlah klaster berubah.

### 3. Batasan XAI

Nilai Shapley menjelaskan **alokasi skor model**, bukan efek kausal kebijakan: menambah EWS tidak otomatis menurunkan skor sebesar nilai kontribusinya karena bobot entropy akan berubah bila data berubah. Baseline “profil teraman” adalah konstruksi analitis, bukan target kebijakan nyata. Dekomposisi margin juga hanya menjelaskan jarak pada ruang fitur terstandar, bukan penyebab sosial-ekonomi penugasan klaster.

---

## ⚠️ Catatan & Limitasi

1. **Dominasi satu kriteria pada pembobotan entropi.** `n_alat_dini` memperoleh bobot 0,48 karena sebarannya sangat timpang (32 dari 42 kecamatan bernilai 0 unit, maksimum 2 unit). Akibatnya skor TOPSIS berperilaku hampir seperti *switch* biner "punya EWS / tidak": 10 kecamatan teratas semuanya tanpa EWS, dan 10 kecamatan yang memiliki EWS menempati peringkat 33–42. Analisis Shapley pada `05_xai.ipynb` mengonfirmasi dominasi ini secara eksplisit: `n_alat_dini` menyumbang rata-rata 0,510 poin $C_i$ (85,3% dari total |φ|), jauh di atas `jiwa_per_1000` (0,047; 7,9%) dan kriteria lain (≤ 0,015; ≤ 2,6%). Untuk pemakaian kebijakan, bobot ini sebaiknya dibandingkan dengan skema *expert weights* (`skor_expert`) yang tersedia di `topsis_result.csv`.
2. **Arah kriteria *cost* perlu dibaca hati-hati.** Karena `n_alat_dini` bertipe *cost*, nilai 0 unit secara matematis mendekatkan kecamatan ke solusi ideal dan menaikkan skor. Interpretasinya adalah "minim kapasitas EWS = urgensi tinggi", bukan "tanpa EWS = kondisi baik". Narasi ini harus ditulis eksplisit di dashboard.
3. **Tumpang-tindih fitur yang disengaja.** `jiwa_per_1000` dan `kepadatan_jiwa_km2` adalah kriteria TOPSIS sekaligus fitur K-Means. Alternatif tanpa tumpang-tindih sudah diuji di `03_kmeans.ipynb` dan menghasilkan klaster yang tidak konsisten dengan peringkat TOPSIS (hanya 7/10 top-10 masuk klaster tertinggi), sehingga kombinasi saat ini dipertahankan.
4. **Data statis.** Seluruh analisis memakai agregat Satu Data Jakarta 2013–2024 dan belum memperbarui otomatis; pembaruan data menuntut eksekusi ulang pipeline 01 → 05.

---

## 📚 Referensi

* Ashari et al. (2023), *Elbow, Silhouette, Davies-Bouldin, Calinski-Harabasz, and Rand-Index Evaluation on K-Means for Classifying Flood-Affected Areas in Jakarta*, JAIC 7(1):95–103.
* Hwang, C. L., & Yoon, K. (1981), *Multiple Attribute Decision Making: Methods and Applications*, Springer-Verlag.
* Shannon, C. E. (1948), *A Mathematical Theory of Communication*, Bell System Technical Journal, 27(3), 379–423.
