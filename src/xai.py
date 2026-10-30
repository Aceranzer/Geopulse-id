"""
Modul Explainable AI (XAI) untuk GeoPulse-id
Proyek: GeoPulse-id (Prioritas Mitigasi Banjir DKI Jakarta)

Modul ini menyediakan dua lapis penjelasan:

1. TOPSIS -- nilai Shapley eksak untuk setiap kriteria. Karena jumlah kriteria
   hanya 8, seluruh 2^8 koalisi dapat dienumerasi sehingga kontribusi tiap
   kriteria bersifat eksak (bukan aproksimasi), aditif, dan memenuhi
   efisiensi: sum_j(phi_ij) = Ci_i - Ci_baseline.
2. K-Means -- kepentingan fitur pada partisi klaster dan dekomposisi margin
   penugasan tiap kecamatan terhadap klaster pesaing terdekatnya.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Sequence

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# TOPSIS: model rujukan tetap + nilai Shapley eksak
# ---------------------------------------------------------------------------
def _as_criteria_types(criteria_types: Sequence[str]) -> np.ndarray:
    types = np.array([str(t).lower().strip() for t in criteria_types], dtype=object)
    invalid = sorted(set(types) - {"benefit", "cost"})
    if invalid:
        raise ValueError(f"Tipe kriteria harus 'benefit' atau 'cost', ditemukan: {invalid}")
    return types


def topsis_reference_score(
    X: np.ndarray,
    X_ref: np.ndarray,
    weights: np.ndarray,
    criteria_types: Sequence[str],
    eps: float = 1e-12,
) -> np.ndarray:
    """
    Hitung skor TOPSIS untuk X menggunakan patokan tetap dari X_ref.

    Normalisasi vektor, solusi ideal positif (A+), dan solusi ideal negatif
    (A-) dihitung sekali dari X_ref. Nilai X kemudian dipetakan ke patokan
    tersebut. Fungsi ini penting agar XAI memperlakukan TOPSIS sebagai fungsi
    deterministik per alternatif, bukan model yang ikut berubah ketika satu
    kriteria diganti dengan nilai baseline.

    Parameters
    ----------
    X : np.ndarray (m x n)
        Matriks keputusan yang akan dinilai.
    X_ref : np.ndarray (m_ref x n)
        Matriks rujukan untuk menghitung normalisasi dan solusi ideal.
    weights : np.ndarray (n,)
        Bobot kriteria.
    criteria_types : Sequence[str]
        'benefit' atau 'cost' untuk tiap kriteria.
    eps : float
        Epsilon stabilitas numerik.

    Returns
    -------
    C : np.ndarray (m,)
        Skor preferensi TOPSIS.
    """
    X = np.asarray(X, dtype=float)
    X_ref = np.asarray(X_ref, dtype=float)
    w = np.asarray(weights, dtype=float)
    types = _as_criteria_types(criteria_types)

    if X.ndim != 2 or X_ref.ndim != 2:
        raise ValueError("X dan X_ref harus matriks 2 dimensi")
    if X.shape[1] != X_ref.shape[1] or X.shape[1] != len(w) or X.shape[1] != len(types):
        raise ValueError("Jumlah kolom X, X_ref, bobot, dan tipe kriteria harus sama")

    norm = np.sqrt(np.sum(X_ref**2, axis=0, keepdims=True))
    V_ref = (X_ref / (norm + eps)) * w
    A_pos = np.where(types == "benefit", V_ref.max(axis=0), V_ref.min(axis=0))
    A_neg = np.where(types == "benefit", V_ref.min(axis=0), V_ref.max(axis=0))

    V = (X / (norm + eps)) * w
    D_pos = np.sqrt(np.sum((V - A_pos) ** 2, axis=1))
    D_neg = np.sqrt(np.sum((V - A_neg) ** 2, axis=1))
    return D_neg / (D_pos + D_neg + eps)


def safe_baseline(X: np.ndarray, criteria_types: Sequence[str]) -> np.ndarray:
    """
    Profil acuan 'teraman' dari data: benefit = nilai minimum, cost = maksimum.

    Profil ini adalah kecamatan sintetis dengan seluruh indikator bahaya dan
    kerentanan pada nilai terendah serta kapasitas EWS pada nilai tertinggi.
    Skor TOPSIS profil ini tepat 0, sehingga kontribusi Shapley dapat dibaca
    sebagai kenaikan skor dari kondisi teraman menuju kondisi aktual.
    """
    X = np.asarray(X, dtype=float)
    types = _as_criteria_types(criteria_types)
    return np.where(types == "benefit", X.min(axis=0), X.max(axis=0))


def exact_shapley_topsis(
    X: np.ndarray,
    weights: np.ndarray,
    criteria_types: Sequence[str],
    feature_names: Sequence[str] | None = None,
    baseline: np.ndarray | None = None,
    index: Sequence | None = None,
    eps: float = 1e-12,
) -> pd.DataFrame:
    """
    Nilai Shapley eksak tiap kriteria terhadap skor TOPSIS.

    Untuk setiap koalisi S, kriteria yang tidak masuk S diganti dengan nilai
    profil baseline. Nilai permainan v(S) adalah skor TOPSIS alternatif dengan
    kriteria di S memakai nilai aktual dan lainnya memakai baseline. Nilai
    Shapley kemudian dihitung dari rata-rata kontribusi marginal:

        phi_j = sum_{S subset N\\{j}} |S|!(n-|S|-1)!/n! * [v(S+j) - v(S)]

    Dengan baseline 'teraman', v(empty) = 0 dan sum_j(phi_j) = Ci.

    Parameters
    ----------
    X : np.ndarray (m x n)
        Matriks keputusan 42 kecamatan x 8 kriteria.
    weights : np.ndarray (n,)
        Bobot kriteria (mis. bobot Shannon Entropy).
    criteria_types : Sequence[str]
        'benefit' atau 'cost' untuk tiap kriteria.
    feature_names : Sequence[str] | None
        Nama kolom; default 'x1', ..., 'xn'.
    baseline : np.ndarray | None
        Profil acuan (n,). Default: safe_baseline(X, criteria_types).
    index : Sequence | None
        Label baris (mis. nama kecamatan). Default: RangeIndex.
    eps : float
        Epsilon stabilitas numerik.

    Returns
    -------
    phi : pd.DataFrame (m x n)
        Kontribusi Shapley tiap kriteria. Atribut tambahan:
        - ``base_value``: skor TOPSIS profil baseline (0 untuk baseline aman)
        - ``prediction``: skor TOPSIS aktual tiap baris
        - ``baseline``: vektor profil acuan
        - ``weights``: vektor bobot
    """
    X = np.asarray(X, dtype=float)
    w = np.asarray(weights, dtype=float)
    types = _as_criteria_types(criteria_types)
    n_features = X.shape[1]

    if X.ndim != 2:
        raise ValueError("X harus matriks 2 dimensi")
    if len(w) != n_features or len(types) != n_features:
        raise ValueError("Panjang bobot/tipe kriteria tidak sama dengan jumlah kolom X")
    if feature_names is None:
        feature_names = [f"x{j + 1}" for j in range(n_features)]
    if len(feature_names) != n_features:
        raise ValueError("Panjang feature_names tidak sama dengan jumlah kolom X")
    if index is not None and len(index) != X.shape[0]:
        raise ValueError("Panjang index tidak sama dengan jumlah baris X")

    if baseline is None:
        base = safe_baseline(X, types)
    else:
        base = np.asarray(baseline, dtype=float).reshape(-1)
        if len(base) != n_features:
            raise ValueError("Panjang baseline tidak sama dengan jumlah kriteria")

    # Nilai permainan untuk seluruh 2^n koalisi (n=8 -> 256 evaluasi).
    n_masks = 1 << n_features
    values = np.empty((n_masks, X.shape[0]), dtype=float)
    for mask in range(n_masks):
        X_coalition = np.tile(base, (X.shape[0], 1))
        for j in range(n_features):
            if mask & (1 << j):
                X_coalition[:, j] = X[:, j]
        values[mask] = topsis_reference_score(X_coalition, X, w, types, eps=eps)

    phi = np.zeros_like(X, dtype=float)
    for j in range(n_features):
        others = [k for k in range(n_features) if k != j]
        for size in range(n_features):
            weight = (
                math.factorial(size)
                * math.factorial(n_features - size - 1)
                / math.factorial(n_features)
            )
            for subset in itertools.combinations(others, size):
                mask = sum(1 << k for k in subset)
                phi[:, j] += weight * (values[mask | (1 << j)] - values[mask])

    result = pd.DataFrame(phi, columns=list(feature_names), index=index)
    # Atribut disimpan sebagai tipe skalar/list (bukan ndarray/Series) agar
    # operasi pandas seperti melt/stack tidak gagal saat membandingkan attrs.
    result.attrs["base_value"] = float(values[0].mean())
    result.attrs["prediction"] = values[n_masks - 1].tolist()
    result.attrs["baseline"] = base.tolist()
    result.attrs["weights"] = w.tolist()
    return result


def shapley_global_importance(
    phi: pd.DataFrame,
    weights: Sequence[float] | None = None,
    criteria_meta: dict[str, dict] | None = None,
) -> pd.DataFrame:
    """
    Ringkas nilai Shapley menjadi kepentingan global per kriteria.

    Parameters
    ----------
    phi : pd.DataFrame
        Output ``exact_shapley_topsis``.
    weights : Sequence[float] | None
        Bobot kriteria (opsional), ditambahkan sebagai kolom ``bobot``.
    criteria_meta : dict | None
        Metadata kriteria, mis. ``{'kolom': {'dimensi': ..., 'type': ...}}``.

    Returns
    -------
    pd.DataFrame
        Kolom: rata_rata_abs, rata_rata_bertanda, share_abs, std, n;
        ditambah bobot/dimensi/tipe bila tersedia. Terurut menurun berdasarkan
        ``rata_rata_abs``.
    """
    abs_phi = phi.abs()
    out = pd.DataFrame(
        {
            "rata_rata_abs": abs_phi.mean(axis=0),
            "rata_rata_bertanda": phi.mean(axis=0),
            "std": phi.std(axis=0, ddof=1),
            "n": phi.notna().sum(axis=0),
        },
        index=phi.columns,
    )
    total = out["rata_rata_abs"].sum()
    out["share_abs"] = out["rata_rata_abs"] / total if total > 0 else 0.0

    if weights is not None:
        w = np.asarray(weights, dtype=float)
        if len(w) != len(out):
            raise ValueError("Panjang bobot tidak sama dengan jumlah kriteria")
        out["bobot"] = w
    if criteria_meta is not None:
        out["dimensi"] = [criteria_meta.get(c, {}).get("dimensi", "") for c in out.index]
        out["tipe"] = [criteria_meta.get(c, {}).get("type", "") for c in out.index]

    return out.sort_values("rata_rata_abs", ascending=False)


def explain_local(phi: pd.DataFrame, alternative: str | int) -> pd.DataFrame:
    """
    Tabel kontribusi lokal satu alternatif, terurut dari |kontribusi| terbesar.

    Returns
    -------
    pd.DataFrame
        Kolom ``kontribusi``, ``abs_kontribusi``, ``share_abs``, dan
        ``kumulatif`` (mulai dari 0 menuju skor akhir).
    """
    row = phi.loc[alternative]
    out = pd.DataFrame({"kontribusi": row.astype(float)})
    out["abs_kontribusi"] = out["kontribusi"].abs()
    out = out.sort_values("abs_kontribusi", ascending=False)
    total = out["abs_kontribusi"].sum()
    out["share_abs"] = out["abs_kontribusi"] / total if total > 0 else 0.0
    out["kumulatif"] = out["kontribusi"].cumsum()
    return out


# ---------------------------------------------------------------------------
# K-Means: kepentingan fitur dan dekomposisi margin penugasan
# ---------------------------------------------------------------------------
def _cluster_centers(Z: np.ndarray, labels: np.ndarray) -> np.ndarray:
    classes = np.unique(labels)
    return np.vstack([Z[labels == c].mean(axis=0) for c in classes])


def kmeans_feature_importance(
    Z: np.ndarray | pd.DataFrame,
    labels: Sequence[int],
) -> pd.DataFrame:
    """
    Kepentingan fitur pada partisi K-Means berbasis between-cluster sum of squares.

    SSB_j = sum_k n_k * (mu_kj - mu_j)^2. Kolom ``share`` adalah proporsi SSB
    fitur terhadap total SSB seluruh fitur; kolom ``eta2`` adalah SSB_j / SST_j
    (proporsi variansi fitur yang dijelaskan oleh klaster).

    Parameters
    ----------
    Z : np.ndarray | pd.DataFrame
        Matriks fitur terstandar (n_samples x n_features).
    labels : Sequence[int]
        Label klaster tiap baris.

    Returns
    -------
    pd.DataFrame
        Terurut menurun berdasarkan ``share``.
    """
    if isinstance(Z, pd.DataFrame):
        feature_names = list(Z.columns)
        values = Z.values.astype(float)
    else:
        values = np.asarray(Z, dtype=float)
        feature_names = [f"z{j + 1}" for j in range(values.shape[1])]
    labels = np.asarray(labels)

    if values.ndim != 2 or len(labels) != len(values):
        raise ValueError("Z dan labels harus memiliki jumlah baris yang sama")

    grand_mean = values.mean(axis=0)
    ssb = np.zeros(values.shape[1], dtype=float)
    sst = np.sum((values - grand_mean) ** 2, axis=0)
    for c in np.unique(labels):
        n_k = int((labels == c).sum())
        center = values[labels == c].mean(axis=0)
        ssb += n_k * (center - grand_mean) ** 2

    out = pd.DataFrame(
        {
            "ss_between": ssb,
            "share": ssb / ssb.sum() if ssb.sum() > 0 else 0.0,
            "eta2": np.divide(ssb, sst, out=np.zeros_like(ssb), where=sst > 0),
        },
        index=feature_names,
    )
    return out.sort_values("share", ascending=False)


def cluster_assignment_contributions(
    Z: np.ndarray | pd.DataFrame,
    labels: Sequence[int],
    centers: np.ndarray | None = None,
    cluster_names: dict[int, str] | None = None,
) -> pd.DataFrame:
    """
    Dekomposisi fitur dari margin penugasan klaster tiap sampel.

    Untuk sampel i, klaster sendiri k dan klaster pesaing terdekat l:

        margin_i = ||z_i - c_k||^2 - ||z_i - c_l||^2
                 = sum_j [ (z_ij - c_kj)^2 - (z_ij - c_lj)^2 ]

    Margin negatif berarti sampel lebih dekat ke klaster sendiri. Kontribusi
    fitur negatif berarti fitur tersebut **menjaga** sampel di klaster sendiri;
    kontribusi positif berarti fitur tersebut **mendorong** sampel ke klaster
    pesaing (sinyal kecamatan batas).

    Returns
    -------
    pd.DataFrame
        Kontribusi per fitur (baris = sampel, kolom = fitur). Atribut:
        ``own_cluster``, ``competitor``, ``margin``, ``own_distance2``,
        ``competitor_distance2``, ``center``.
    """
    if isinstance(Z, pd.DataFrame):
        feature_names = list(Z.columns)
        index = Z.index
        values = Z.values.astype(float)
    else:
        values = np.asarray(Z, dtype=float)
        feature_names = [f"z{j + 1}" for j in range(values.shape[1])]
        index = pd.RangeIndex(len(values))
    labels = np.asarray(labels)

    if values.ndim != 2 or len(labels) != len(values):
        raise ValueError("Z dan labels harus memiliki jumlah baris yang sama")

    classes = np.unique(labels)
    order = np.argsort(classes)
    classes = classes[order]
    if centers is None:
        centers = _cluster_centers(values, labels)
    centers = np.asarray(centers, dtype=float)
    if centers.shape != (len(classes), values.shape[1]):
        raise ValueError("Bentuk centers tidak sesuai dengan jumlah klaster/fitur")

    class_to_pos = {c: i for i, c in enumerate(classes)}
    distances2 = np.sum((values[:, None, :] - centers[None, :, :]) ** 2, axis=2)

    own_pos = np.array([class_to_pos[c] for c in labels])
    own_dist = distances2[np.arange(len(values)), own_pos]
    competitor_pos = np.empty(len(values), dtype=int)
    for i in range(len(values)):
        masked = distances2[i].copy()
        masked[own_pos[i]] = np.inf
        competitor_pos[i] = int(np.argmin(masked))
    competitor_dist = distances2[np.arange(len(values)), competitor_pos]

    contrib = (values - centers[own_pos]) ** 2 - (
        values - centers[competitor_pos]
    ) ** 2
    result = pd.DataFrame(contrib, index=index, columns=feature_names)
    result.attrs["own_cluster"] = classes[own_pos].tolist()
    result.attrs["competitor"] = classes[competitor_pos].tolist()
    result.attrs["margin"] = (own_dist - competitor_dist).tolist()
    result.attrs["own_distance2"] = own_dist.tolist()
    result.attrs["competitor_distance2"] = competitor_dist.tolist()
    result.attrs["center"] = centers.tolist()
    result.attrs["classes"] = classes.tolist()
    if cluster_names is not None:
        result.attrs["own_cluster_name"] = [cluster_names.get(int(c), str(c)) for c in classes[own_pos]]
        result.attrs["competitor_name"] = [cluster_names.get(int(c), str(c)) for c in classes[competitor_pos]]
    return result


def boundary_cases(
    contributions: pd.DataFrame,
    n: int = 6,
    index: Sequence | None = None,
) -> pd.DataFrame:
    """
    Pilih n sampel batas untuk dijelaskan secara lokal.

    Bila ``index`` diberikan (mis. n sampel dengan silhouette terendah dari
    tahap K-Means), urutan tersebut dipakai. Bila tidak, dipilih n sampel
    dengan margin penugasan paling tipis (paling ambigu).

    Returns
    -------
    pd.DataFrame
        Kontribusi fitur untuk sampel batas, dengan kolom tambahan
        ``margin`` dan ``klaster_pesaing``.
    """
    margin = pd.Series(contributions.attrs["margin"], index=contributions.index)
    competitor = pd.Series(contributions.attrs["competitor"], index=contributions.index)
    own = pd.Series(contributions.attrs["own_cluster"], index=contributions.index)
    if index is None:
        # margin selalu <= 0 (klaster sendiri adalah yang terdekat); nilai
        # paling mendekati 0 = penugasan paling ambigu.
        idx = margin.sort_values(ascending=False).head(n).index
    else:
        idx = pd.Index(index)[:n]

    out = contributions.loc[idx].copy()
    out.insert(0, "margin", margin.loc[idx])
    out.insert(0, "klaster_pesaing", competitor.loc[idx].values)
    out.insert(0, "klaster", own.loc[idx].values)
    return out.sort_values("margin")


__all__ = [
    "topsis_reference_score",
    "safe_baseline",
    "exact_shapley_topsis",
    "shapley_global_importance",
    "explain_local",
    "kmeans_feature_importance",
    "cluster_assignment_contributions",
    "boundary_cases",
]
