"""
Modul Multi-Criteria Decision Making: AHP & TOPSIS
Proyek: GeoPulse-id (Prioritas Mitigasi Banjir DKI Jakarta)
"""

import numpy as np
import pandas as pd

# Tabel Random Index (RI) standar Saaty (1980) untuk n = 1 sampai 10
SAATY_RI = {
    1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12,
    6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49
}


def ahp_weights(pairwise_matrix: np.ndarray) -> tuple[np.ndarray, float, float, float]:
    """
    Menghitung bobot kriteria menggunakan Analytic Hierarchy Process (AHP)
    serta melakukan uji konsistensi matriks perbandingan berpasangan (Pairwise Comparison).

    Parameters:
    -----------
    pairwise_matrix : np.ndarray (shape: n x n)
        Matriks perbandingan berpasangan dengan skala Saaty 1-9.
        Harus bersifat reciprocal: A[i, j] = 1 / A[j, i] dan A[i, i] = 1.

    Returns:
    --------
    weights : np.ndarray (shape: n,)
        Vektor bobot prioritas kriteria (sum = 1.0).
    lambda_max : float
        Nilai eigenvalue terbesar.
    CI : float
        Consistency Index.
    CR : float
        Consistency Ratio. Nilai CR < 0.10 menandakan matriks perbandingan konsisten.
    """
    A = np.array(pairwise_matrix, dtype=float)
    n = A.shape[0]
    assert A.shape[0] == A.shape[1], "Matriks perbandingan harus persegi (n x n)"

    # 1. Normalisasi matriks per kolom
    col_sums = A.sum(axis=0)
    norm_A = A / col_sums

    # 2. Hitung vektor prioritas (bobot w) sebagai rata-rata baris
    weights = norm_A.mean(axis=1)

    # 3. Uji Konsistensi (Consistency Test)
    # Aw = A dot w
    Aw = np.dot(A, weights)
    # lambda_max = rata-rata dari (Aw / w)
    lambda_max = float(np.mean(Aw / weights))

    # Consistency Index (CI)
    CI = float((lambda_max - n) / (n - 1)) if n > 1 else 0.0

    # Consistency Ratio (CR)
    RI = SAATY_RI.get(n, 1.49)
    CR = float(CI / RI) if RI > 0 else 0.0

    return weights, lambda_max, CI, CR


def shannon_entropy_weights(X: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """
    Menghitung bobot objektif kriteria menggunakan metode Shannon Entropy (pembanding).
    """
    m, n = X.shape
    col_sums = X.sum(axis=0, keepdims=True)
    P = X / (col_sums + eps)
    P = np.where(P <= 0, eps, P)

    k = 1.0 / np.log(m)
    E = -k * np.sum(P * np.log(P), axis=0)
    d = 1.0 - E

    if d.sum() == 0:
        return np.ones(n) / n

    weights = d / d.sum()
    return weights


def topsis(
    X: np.ndarray,
    weights: np.ndarray,
    criteria_types: list[str],
    eps: float = 1e-12
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Eksekusi algoritma TOPSIS Murni (Technique for Order of Preference by Similarity to Ideal Solution).

    Parameters:
    -----------
    X : np.ndarray (shape: m x n)
        Matriks keputusan (m baris alternatif, n kolom kriteria).
    weights : np.ndarray (shape: n,)
        Vektor bobot tiap kriteria (sum = 1.0).
    criteria_types : list[str]
        List tipe tiap kriteria, bernilai 'benefit' atau 'cost'.
    eps : float
        Epsilon untuk stabilitas numerik.

    Returns:
    --------
    C : np.ndarray (shape: m,)
        Skor preferensi / kedekatan relatif (skor TOPSIS, rentang 0-1).
    D_pos : np.ndarray (shape: m,)
        Jarak Euclidean ke Solusi Ideal Positif (A+).
    D_neg : np.ndarray (shape: m,)
        Jarak Euclidean ke Solusi Ideal Negatif (A-).
    A_pos : np.ndarray (shape: n,)
        Vektor Solusi Ideal Positif.
    A_neg : np.ndarray (shape: n,)
        Vektor Solusi Ideal Negatif.
    """
    m, n = X.shape
    assert len(weights) == n, f"Panjang bobot ({len(weights)}) tidak sama dengan kriteria ({n})"
    assert len(criteria_types) == n, f"Panjang criteria_types ({len(criteria_types)}) tidak sama dengan kriteria ({n})"

    # Langkah 1: Normalisasi Vektor
    norm = np.sqrt(np.sum(X**2, axis=0, keepdims=True))
    R = X / (norm + eps)

    # Langkah 2: Matriks Ternormalisasi Terbobot
    V = R * weights

    # Langkah 3: Solusi Ideal Positif (A+) dan Solusi Ideal Negatif (A-)
    A_pos = np.zeros(n)
    A_neg = np.zeros(n)
    for j, c_type in enumerate(criteria_types):
        c_type_lower = c_type.lower().strip()
        if c_type_lower == "benefit":
            A_pos[j] = np.max(V[:, j])
            A_neg[j] = np.min(V[:, j])
        elif c_type_lower == "cost":
            A_pos[j] = np.min(V[:, j])
            A_neg[j] = np.max(V[:, j])
        else:
            raise ValueError(f"Tipe kriteria harus 'benefit' atau 'cost', ditemukan: {c_type}")

    # Langkah 4: Jarak Euclidean
    D_pos = np.sqrt(np.sum((V - A_pos)**2, axis=1))
    D_neg = np.sqrt(np.sum((V - A_neg)**2, axis=1))

    # Langkah 5: Kedekatan Relatif (Skor TOPSIS Ci)
    C = D_neg / (D_pos + D_neg + eps)

    return C, D_pos, D_neg, A_pos, A_neg


class TOPSISSolver:
    """
    Wrapper class untuk mempermudah pemakaian AHP-TOPSIS dengan DataFrame pandas.
    """
    def __init__(self, criteria_dict: dict[str, dict]):
        self.criteria_dict = criteria_dict
        self.cols = list(criteria_dict.keys())
        self.criteria_types = [criteria_dict[col].get("type", "benefit") for col in self.cols]
        self.weights = None

    def set_weights(self, weights: np.ndarray | list[float]):
        """Set bobot langsung (misal dari hasil perhitungan AHP)."""
        w = np.array(weights, dtype=float)
        self.weights = w / w.sum()

    def evaluate(self, df: pd.DataFrame, weights: np.ndarray | None = None) -> pd.DataFrame:
        if weights is not None:
            self.set_weights(weights)
        assert self.weights is not None, "Bobot belum ditentukan! Panggil set_weights terlebih dahulu."

        X = df[self.cols].values.astype(float)
        C, D_pos, D_neg, A_pos, A_neg = topsis(X, self.weights, self.criteria_types)

        result_df = df.copy()
        result_df["skor_topsis"] = C
        result_df["D_pos"] = D_pos
        result_df["D_neg"] = D_neg
        result_df["rank_topsis"] = result_df["skor_topsis"].rank(ascending=False).astype(int)

        return result_df
