# Geopulse-id

Pengembangan Sistem Pendukung Keputusan Berbasis Dashboard Analitik dengan Integrasi K-Means Clustering dan TOPSIS untuk Prioritas Mitigasi Banjir di DKI Jakarta

Pipeline data mining: data Satu Data Jakarta → K-Means (klaster wilayah rawan banjir) → dashboard Streamlit.
Cakupan: 42 kecamatan (Kepulauan Seribu tidak diikutkan).

## Struktur

```
Data/Raw/            # file asli + kecamatan.geojson
Data/                # dki_master.csv, clustered_result.csv, figures/
notebook/
  01_data.ipynb              # understanding, preparation, EDA
  03_kmeans_NoTopsis.ipynb   # elbow, K-Means, validasi, peta
```

Berikutnya: `04_viz.ipynb`, `src/`, `app.py` (Streamlit).

## Menjalankan

```bash
pip install pandas numpy scikit-learn geopandas matplotlib seaborn lxml jupyter
```

Jalankan notebook berurutan `01 → 03`.

## Metode

**K-Means** pada 9 fitur banjir dan demografi per kecamatan (`log1p` untuk fitur miring, winsorize 5%, filter korelasi r > 0,9, StandardScaler). Jumlah klaster k = 4, dicek dengan Elbow, Silhouette, DBI, CH, dan stabilitas (ARI).

## Hasil (tanpa TOPSIS, k = 4)

| Metrik | Nilai |
|---|---|
| Silhouette | 0,213 |
| Davies-Bouldin | 1,353 |
| Calinski-Harabasz | 14,3 |
| ARI seed / bootstrap | 0,83 / 0,73 |
| Ukuran klaster | 18 / 13 / 7 / 4 |

## Keterbatasan

Data banjir diagregasi dari kelurahan, hanya 8 tahun tidak berurutan, data meteorologi tidak dipakai (hanya 5 stasiun dan tumpang tindih dengan data banjir hanya di 2024).

## Referensi

Ashari et al. (2023), *Elbow, Silhouette, Davies-Bouldin, Calinski-Harabasz, and Rand-Index Evaluation on K-Means for Classifying Flood-Affected Areas in Jakarta*, JAIC 7(1):95–103.
