"""
Pipeline TOPSIS + K-Means untuk website Geopulse-ID.

Logika dipindahkan dari notebook 02_topsis.ipynb dan 03_kmeans.ipynb
tanpa mengubah hasil. Input: tabel master 42 kecamatan (data/dki_master.csv).
Membuat tabel master dari file mentah tetap dilakukan 01_data.ipynb (butuh geopandas).
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.cluster import AgglomerativeClustering, KMeans
from sklearn.metrics import (adjusted_rand_score, calinski_harabasz_score,
                             davies_bouldin_score, silhouette_samples, silhouette_score)
from sklearn.preprocessing import StandardScaler

from src.topsis import shannon_entropy_weights, topsis

# 8 kriteria (urutan sama dengan 02_topsis.ipynb)
CRITERIA = {
    "frek_tahun_banjir":      {"dimensi": "Bahaya",     "type": "benefit", "satuan": "proporsi (0-1)", "desc": "Proporsi tahun terjadi banjir"},
    "bulan_banjir_per_tahun": {"dimensi": "Bahaya",     "type": "benefit", "satuan": "bulan/tahun",    "desc": "Rata-rata bulan banjir per tahun"},
    "kejadian_per_tahun":     {"dimensi": "Bahaya",     "type": "benefit", "satuan": "kejadian/tahun", "desc": "Frekuensi banjir tahunan"},
    "tinggi_max_cm":          {"dimensi": "Bahaya",     "type": "benefit", "satuan": "cm",             "desc": "Ketinggian genangan maksimal"},
    "lama_hari_mean":         {"dimensi": "Bahaya",     "type": "benefit", "satuan": "hari",           "desc": "Rata-rata durasi genangan"},
    "jiwa_per_1000":          {"dimensi": "Bahaya",     "type": "benefit", "satuan": "jiwa/1000 pddk", "desc": "Penduduk terdampak per 1000 warga"},
    "kepadatan_jiwa_km2":     {"dimensi": "Kerentanan", "type": "benefit", "satuan": "jiwa/km2",       "desc": "Kepadatan penduduk wilayah"},
    "n_alat_dini":            {"dimensi": "Kapasitas",  "type": "cost",    "satuan": "unit EWS",       "desc": "Jumlah alat peringatan dini (EWS)"},
}
CRIT_COLS = list(CRITERIA)
CRIT_TYPES = [CRITERIA[c]["type"] for c in CRIT_COLS]

# bobot pakar (sama dengan 02_topsis.ipynb)
W_EXPERT = np.array([0.10, 0.15, 0.15, 0.10, 0.10, 0.20, 0.10, 0.10])
W_EXPERT = W_EXPERT / W_EXPERT.sum()

# skema pembanding 6 kriteria (tanpa durasi genangan dan alat dini), seperti di 02_topsis.ipynb
CRIT_6 = ["frek_tahun_banjir", "bulan_banjir_per_tahun", "kejadian_per_tahun", "tinggi_max_cm", "jiwa_per_1000", "kepadatan_jiwa_km2"]

CLUSTER_FEATURES = ["skor_topsis", "jiwa_per_1000", "kepadatan_jiwa_km2"]
K_FINAL = 4
SEED = 42
CLUSTER_NAMES = ["Prioritas Tinggi", "Waspada", "Menengah", "Rendah"]
CLUSTER_COLORS = ["#8B0000", "#E4572E", "#F6C85F", "#B7E4A7"]   # merah tua, jingga, kuning, hijau
SILHOUETTE_BATAS = 0.1   # silhouette per kecamatan di bawah ini = kecamatan batas (klaster kurang pasti)


def filter_kecamatan(master: pd.DataFrame) -> pd.DataFrame:
    """Buang Kepulauan Seribu; urutan baris dipertahankan."""
    is_seribu = master.wilayah.str.contains("SERIBU", na=False) | master.kecamatan.str.contains("SERIBU", na=False)
    return master[~is_seribu].copy().reset_index(drop=True)


def compute_topsis(df_kec: pd.DataFrame) -> pd.DataFrame:
    """Skor TOPSIS dengan bobot entropi, sama rata, dan pakar."""
    X = df_kec[CRIT_COLS].values.astype(float)
    n = X.shape[1]
    weights = {"entropi": shannon_entropy_weights(X), "sama": np.ones(n) / n, "pakar": W_EXPERT}

    out = df_kec.copy()
    C, D_pos, D_neg, _, _ = topsis(X, weights["entropi"], CRIT_TYPES)
    out["skor_topsis"], out["D_pos"], out["D_neg"] = C, D_pos, D_neg
    out["rank_topsis"] = out.skor_topsis.rank(ascending=False).astype(int)
    for nama, kode in [("sama", "equal"), ("pakar", "expert")]:
        out[f"skor_{kode}"] = topsis(X, weights[nama], CRIT_TYPES)[0]
        out[f"rank_{kode}"] = out[f"skor_{kode}"].rank(ascending=False).astype(int)
    X6 = df_kec[CRIT_6].values.astype(float)
    out["skor_topsis_6kriteria"] = topsis(X6, shannon_entropy_weights(X6), ["benefit"] * len(CRIT_6))[0]
    out["rank_topsis_6kriteria"] = out.skor_topsis_6kriteria.rank(ascending=False).astype(int)
    out.attrs["weights"] = weights
    return out


def _order_labels(lab, skor):
    """Relabel: id 0 = rata-rata skor TOPSIS tertinggi ... id K-1 = terendah."""
    order = pd.Series(skor).groupby(lab).mean().sort_values(ascending=False).index.tolist()
    return np.array([order.index(l) for l in lab])


def build_features(base: pd.DataFrame) -> pd.DataFrame:
    """log1p pada fitur miring, winsorize 5% pada fitur ber-outlier, buang korelasi > 0.9, lalu StandardScaler."""
    X = base[CLUSTER_FEATURES].copy()
    X = X.fillna(X.median())
    q1, q3 = X.quantile(.25), X.quantile(.75)
    out = (X < q1 - 1.5 * (q3 - q1)) | (X > q3 + 1.5 * (q3 - q1))

    log_cols = [k for k in X.columns if k != "skor_topsis" and X[k].skew() > 1 and (X[k] >= 0).all()]
    Xt = X.copy()
    Xt[log_cols] = np.log1p(Xt[log_cols])
    for k in X.columns[out.any()]:
        if k != "skor_topsis":
            lo, hi = Xt[k].quantile([.05, .95])
            Xt[k] = Xt[k].clip(lo, hi)

    cr = Xt.corr().abs()
    drop = set()
    for i, a in enumerate(cr.columns):
        for b in cr.columns[i + 1:]:
            if cr.loc[a, b] > 0.90 and a not in drop and b not in drop:
                drop.add(b)
    features = [k for k in Xt.columns if k not in drop]
    return pd.DataFrame(StandardScaler().fit_transform(Xt[features]), index=Xt.index, columns=features)


def sweep_k(Z: pd.DataFrame, skor, rank, ks=range(2, 8)) -> pd.DataFrame:
    """Tabel metrik K-Means untuk k=2..7."""
    top10 = (rank <= 10).values
    rows = []
    for k in ks:
        km = KMeans(k, n_init=50, random_state=SEED).fit(Z)
        lab = _order_labels(km.labels_, skor)
        sz = np.bincount(lab)
        rows.append(dict(
            k=k, inertia=km.inertia_, silhouette=silhouette_score(Z, lab),
            DBI=davies_bouldin_score(Z, lab), CH=calinski_harabasz_score(Z, lab),
            spearman_rank=spearmanr(lab, rank)[0], top10_di_klaster0=int((lab[top10] == 0).sum()),
            ukuran_min=sz.min(), ukuran_maks=sz.max(),
            ARI_vs_ward=adjusted_rand_score(lab, AgglomerativeClustering(k).fit_predict(Z)),
        ))
    return pd.DataFrame(rows).set_index("k")


def compute_clusters(topsis_df: pd.DataFrame):
    """K-Means k=4 atas skor TOPSIS + dampak warga + kepadatan. Mengembalikan (clustered_df, metrics, sweep)."""
    # sama dengan 03_kmeans: baris diindeks nama kecamatan, urutan baris mengikuti master
    base = topsis_df.set_index("kecamatan")
    Z = build_features(base)

    km = KMeans(K_FINAL, n_init=100, random_state=SEED).fit(Z)
    labels = _order_labels(km.labels_, base.skor_topsis.values)

    clustered = pd.DataFrame({
        "kecamatan": base.index,
        "cluster_id": labels,
        "cluster_name": [CLUSTER_NAMES[i] for i in labels],
        "silhouette_sample": silhouette_samples(Z, labels),
        "skor_topsis": base.skor_topsis.values,
        "rank_topsis": base.rank_topsis.values,
    }).sort_values("rank_topsis").reset_index(drop=True)

    metrics = {
        "k": K_FINAL,
        "silhouette": float(silhouette_score(Z, labels)),
        "DBI": float(davies_bouldin_score(Z, labels)),
        "CH": float(calinski_harabasz_score(Z, labels)),
        "ukuran_klaster": {int(i): int(n) for i, n in enumerate(np.bincount(labels))},
    }
    sweep = sweep_k(Z, base.skor_topsis.values, base.rank_topsis)
    return clustered, metrics, sweep


def run_pipeline(master: pd.DataFrame):
    """master (42+2 baris, kolom 'kecamatan') -> (topsis_df, clustered_df, info)."""
    topsis_df = compute_topsis(filter_kecamatan(master))
    clustered_df, metrics, sweep = compute_clusters(topsis_df)
    info = {"weights": topsis_df.attrs["weights"], "metrics": metrics, "sweep": sweep}
    return topsis_df, clustered_df, info


def write_outputs(topsis_df, clustered_df, info, out_dir):
    """Tulis topsis_result.csv, clustered_result.csv, k_sweep.csv, metrics.json ke out_dir."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    topsis_df.to_csv(out / "topsis_result.csv", index=False)
    clustered_df.to_csv(out / "clustered_result.csv", index=False, encoding="utf-8")
    info["sweep"].to_csv(out / "k_sweep.csv")
    metrics = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "n_kecamatan": len(topsis_df),
        "weights": {nama: dict(zip(CRIT_COLS, map(float, w))) for nama, w in info["weights"].items()},
        "metrics": info["metrics"],
    }
    with open(out / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    return metrics


def main(argv=None):
    """python -m src.pipeline --input data/dki_master.csv --output data/"""
    from src.validate import validate_master, validate_result

    ap = argparse.ArgumentParser(description="Hitung TOPSIS + K-Means dari tabel master dan tulis hasilnya.")
    ap.add_argument("--input", default="data/dki_master.csv", help="tabel master 42 kecamatan (+ Kepulauan Seribu)")
    ap.add_argument("--output", default="data/", help="folder tujuan CSV hasil dan metrics.json")
    ap.add_argument("--geojson", default="data/kecamatan_poly.geojson", help="untuk mencocokkan nama kecamatan")
    args = ap.parse_args(argv)

    master = pd.read_csv(args.input)
    with open(args.geojson, encoding="utf-8") as f:
        nama_geojson = [ft["properties"]["kecamatan"] for ft in json.load(f)["features"]]
    galat = validate_master(master, nama_geojson)
    if galat:
        print("Data ditolak:")
        for g in galat:
            print(" -", g)
        return 1

    topsis_df, clustered_df, info = run_pipeline(master)
    for w in validate_result(clustered_df):
        print("Peringatan:", w)
    m = write_outputs(topsis_df, clustered_df, info, args.output)
    print(f"Selesai: {m['n_kecamatan']} kecamatan, silhouette {m['metrics']['silhouette']:.3f}, "
          f"ukuran klaster {list(m['metrics']['ukuran_klaster'].values())} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
