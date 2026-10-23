# Panduan Menjelaskan Metode TOPSIS (GeoPulse-id)
*Cheatsheet & Narasi Presentasi untuk Ujian, Sidang, atau Diskusi Tim*

---

## 🎯 1. Ringkasan Singkat (Elevator Pitch - 30 Detik)

> *"Dalam riset ini, kami menggunakan metode **TOPSIS Murni** yang diintegrasikan dengan **Pembobotan Entropi Shannon** untuk menentukan prioritas mitigasi banjir di 42 kecamatan DKI Jakarta.*  
> *Prinsip utamanya adalah mencari kecamatan mana yang kondisinya **paling dekat dengan skenario bencana terburuk (Solusi Ideal Positif)** dan **paling jauh dari skenario teraman (Solusi Ideal Negatif)**.*  
> *Kriteria yang kami pakai tidak sembarangan, melainkan mengikuti kaidah baku kebencanaan internasional: **Bahaya (Hazard), Kerentanan (Vulnerability), dan Kapasitas (Capacity)**.*  
> *Skor hasil TOPSIS ini kemudian menjadi fitur utama yang diumpankan ke algoritma **K-Means Clustering** untuk mengelompokkan wilayah ke dalam 4 zona aksi mitigasi."*

---

## 💡 2. Poin-Poin Kunci yang Harus Anda Sampaikan

### A. Mengapa Memakai TOPSIS?
1. **Objektif dan Rasional:** Konsep solusi ideal sangat masuk akal dalam manajemen risiko bencana—wilayah yang butuh bantuan darurat adalah yang paling mendekati bencana maksimal dan minim fasilitas pencegahan.
2. **Mampu Menangani Banyak Kriteria (MCDM):** Masalah banjir tidak bisa hanya dilihat dari "ketinggian air saja" atau "korban saja", melainkan kombinasi frekuensi, durasi, kepadatan penduduk, dan kesiapan alat.
3. **Mendukung Kriteria Benefit dan Cost Sekaligus:**
   * Kriteria yang memperparah risiko kita set sebagai **Benefit** (semakin tinggi, semakin gawat).
   * Kriteria penanggulangan/kesiapan kita set sebagai **Cost** (semakin tinggi, semakin aman).

---

### B. Mengapa Memakai Pembobotan Entropi Shannon?
Jika ditanya: *"Dari mana kalian menentukan bobot kriteria? Kenapa tidak pakai asumsi sendiri?"*

**Jawaban Anda:**
> *"Kami menggunakan **Shannon Entropy**, yaitu metode pembobotan **objektif berbasis data**.*  
> *Prinsipnya: kriteria yang memiliki sebaran data paling bervariasi atau unik antar kecamatan akan diberikan bobot lebih besar karena memberikan informasi pembeda yang kuat. Sebaliknya, kriteria yang nilainya hampir seragam di semua kecamatan akan diberi bobot kecil.*  
> *Untuk membuktikan keandalan model, kami juga melakukan **Analisis Sensitivitas** dengan membandingkannya terhadap bobot setara (Equal) dan bobot pakar (Expert) menggunakan uji korelasi rank Spearman."*

---

### C. 5 Langkah Matematis yang Harus Anda Jelaskan di Slide

| Langkah | Nama Langkah | Logika / Penjelasan Sederhana |
| :---: | :--- | :--- |
| **1** | **Normalisasi Vektor ($r_{ij}$)** | Menyamakan skala karena satuan berbeda (ada cm, hari, jiwa, orang/km²). Semua diubah ke skala desimal 0–1 tanpa satuan. |
| **2** | **Matriks Terbobot ($v_{ij}$)** | Mengalikan nilai normalisasi dengan bobot kepentingan kriteria ($w_j$). |
| **3** | **Menentukan $A^+$ dan $A^-$** | • Untuk kriteria bahaya & kerentanan (Benefit): $A^+$ ambil nilai **maksimum**, $A^-$ ambil nilai **minimum**.<br>• Untuk kriteria kapasitas/alat EWS (Cost): $A^+$ ambil nilai **minimum** (paling rawan), $A^-$ ambil nilai **maksimum**. |
| **4** | **Jarak Euclidean ($D^+, D^-$)** | Menghitung seberapa jauh posisi suatu kecamatan dari titik bencana terburuk ($D^+$) dan titik paling aman ($D^-$). |
| **5** | **Skor Kedekatan Relatif ($C_i$)** | Menghitung rasio jarak ke titik aman dibagi total jarak ($C_i = \frac{D^-}{D^+ + D^-}$). Nilai berkisar antara **0 hingga 1**. Semakin mendekati 1 $\rightarrow$ Ranking 1 (Prioritas Tertinggi). |

---

## ❓ 3. Prediksi Pertanyaan Penguji / Dosen & Cara Menjawabnya

### Pertanyaan 1: *"Mengapa Kepulauan Seribu tidak diikutkan?"*
**Jawaban:**
> *"Kabupaten Kepulauan Seribu memiliki karakteristik geografis kepulauan dan mekanisme genangan yang berbeda (murni pasang surut air laut dan luas daratan sangat kecil), sedangkan 42 kecamatan daratan Jakarta menghadapi kombinasi limpasan sungai hulu, rob pesisir, dan sistem drainase perkotaan. Memisahkan Kepulauan Seribu mencegah terjadinya outlier ekstrem yang dapat mendistorsi normalisasi data."*

### Pertanyaan 2: *"Bagaimana kalian menangani kriteria Cost pada alat peringatan dini (EWS)?"*
**Jawaban:**
> *"Di TOPSIS, solusi ideal positif ($A^+$) melambangkan skenario bencana terparah yang membutuhkan intervensi darurat tertinggi. Pada kriteria kapasitas seperti alat EWS, daerah yang paling darurat justru daerah yang **paling sedikit atau belum memiliki EWS**. Oleh karena itu, kriteria EWS diperlakukan sebagai **Cost** (nilai $A^+$ diambil dari nilai terkecil/minimum)."*

### Pertanyaan 3: *"Apa hubungan output TOPSIS ini dengan tugas rekan tim Anda di K-Means?"*
**Jawaban:**
> *"TOPSIS menghasilkan skor preferensi tunggal multidimensi (`skor_topsis`) dan ranking global 1 s.d. 42. Skor ini menjadi fitur representatif tingkat risiko yang kami integrasikan bersama fitur fisik lainnya ke dalam algoritma K-Means untuk mengelompokkan kecamatan ke dalam 4 tipologi prioritas mitigasi (Zona Merah, Kuning, Hijau, Biru) untuk memudahkan alokasi anggaran dan kebijakan Pemprov DKI."*
