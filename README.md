# Geopulse-id

Pengembangan Sistem Pendukung Keputusan Berbasis Dashboard Analitik dengan Integrasi K-Means Clustering dan TOPSIS untuk Prioritas Mitigasi Banjir di DKI Jakarta

Pipeline: data Satu Data Jakarta → TOPSIS (skor risiko) → K-Means (klaster prioritas) → dashboard Streamlit.
Cakupan: 42 kecamatan (Kepulauan Seribu tidak diikutkan).

## Struktur

```
Data/Raw/            # file asli + kecamatan.geojson
Data/                # dki_master.csv, topsis_result.csv, clustered_result.csv, figures/
notebook/
  01_data.ipynb      # understanding, preparation, EDA
  02_topsis.ipynb    # bobot, skor, sensitivitas
  03_kmeans.ipynb    # elbow, K-Means, validasi, peta
```

Berikutnya: `04_viz.ipynb`, `src/`, `app.py` (Streamlit).

## Menjalankan

```bash
pip install pandas numpy scikit-learn geopandas matplotlib seaborn lxml jupyter
```

Jalankan notebook berurutan `01 → 02 → 03`.

## Metode

- **TOPSIS:** 6 kriteria banjir dan kepadatan, bobot entropy (pembanding: equal, expert). Bobot expert masih asumsi.
- **K-Means:** fitur `skor_topsis` + 3 fitur pelengkap, k dipilih dengan Elbow. Klaster 0 = Prioritas Tinggi … 3 = Rendah.

## Hasil (k = 4)

| Metrik | Nilai |
|---|---|
| Silhouette | 0,339 |
| Davies-Bouldin | 0,953 |
| Calinski-Harabasz | 31,4 |
| ARI seed / bootstrap | 0,99 / 0,86 |
| Ukuran klaster | 9 / 11 / 15 / 7 |

## Keterbatasan

Data banjir diagregasi dari kelurahan, hanya 8 tahun tidak berurutan, data meteorologi belum dipakai.

## Referensi

Ashari et al. (2023), *Elbow, Silhouette, Davies-Bouldin, Calinski-Harabasz, and Rand-Index Evaluation on K-Means for Classifying Flood-Affected Areas in Jakarta*, JAIC 7(1):95–103.
