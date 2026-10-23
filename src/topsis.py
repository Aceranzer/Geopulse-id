"""
Modul TOPSIS dan Pembobotan Kriteria (Shannon Entropy)
Proyek: GeoPulse-id (Prioritas Mitigasi Banjir DKI Jakarta)
"""

import numpy as np
import pandas as pd


def shannon_entropy_weights(X: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """
    Menghitung bobot objektif kriteria menggunakan metode Shannon Entropy.
    
    Parameters:
    -----------
    X : np.ndarray (shape: m x n)
        Matriks keputusan (m alternatif, n kriteria).
    eps : float
        Nilai kecil untuk menghindari log(0) dan pembagian dengan 0.
        
    Returns:
    --------
    weights : np.ndarray (shape: n,)
        Bobot ternormalisasi tiap kriteria (jumlah = 1.0).
    """
    m, n = X.shape
    # 1. Normalisasi proporsi p_ij = x_ij / sum_i(x_ij)
    col_sums = X.sum(axis=0, keepdims=True)
    P = X / (col_sums + eps)
    P = np.where(P <= 0, eps, P)
    
    # 2. Hitung entropi e_j = -k * sum_i(p_ij * ln(p_ij))
    k = 1.0 / np.log(m)
    E = -k * np.sum(P * np.log(P), axis=0)
    
    # 3. Hitung derajat dispersi / divergensi d_j = 1 - e_j
    d = 1.0 - E
    
    # Jika variasi 0 pada semua kolom, gunakan bobot merata
    if d.sum() == 0:
        return np.ones(n) / n
        
    # 4. Normalisasi bobot w_j = d_j / sum(d_j)
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
    assert len(weights) == n, f"Panjang bobot ({len(weights)}) tidak sama dengan jumlah kriteria ({n})"
    assert len(criteria_types) == n, f"Panjang criteria_types ({len(criteria_types)}) tidak sama dengan kriteria ({n})"
    
    # Langkah 1: Normalisasi Vektor
    # r_ij = x_ij / sqrt(sum_k(x_kj^2))
    norm = np.sqrt(np.sum(X**2, axis=0, keepdims=True))
    R = X / (norm + eps)
    
    # Langkah 2: Matriks Ternormalisasi Terbobot
    # v_ij = w_j * r_ij
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
            
    # Langkah 4: Jarak Euclidean ke Solusi Ideal Positif (D+) dan Negatif (D-)
    # D_i^+ = sqrt(sum_j((v_ij - A_j^+)^2))
    # D_i^- = sqrt(sum_j((v_ij - A_j^-)^2))
    D_pos = np.sqrt(np.sum((V - A_pos)**2, axis=1))
    D_neg = np.sqrt(np.sum((V - A_neg)**2, axis=1))
    
    # Langkah 5: Kedekatan Relatif / Skor Preferensi (Ci)
    # C_i = D_i^- / (D_i^+ + D_i^-)
    C = D_neg / (D_pos + D_neg + eps)
    
    return C, D_pos, D_neg, A_pos, A_neg


class TOPSISSolver:
    """
    Wrapper class untuk mempermudah pemakaian TOPSIS dengan DataFrame pandas.
    """
    def __init__(self, criteria_dict: dict[str, dict]):
        """
        criteria_dict format:
        {
            'nama_kolom': {'type': 'benefit'|'cost', 'weight': float (opsional), 'dim': str, 'desc': str},
            ...
        }
        """
        self.criteria_dict = criteria_dict
        self.cols = list(criteria_dict.keys())
        self.criteria_types = [criteria_dict[col].get("type", "benefit") for col in self.cols]
        self.weights = None
        
    def fit_entropy(self, df: pd.DataFrame) -> np.ndarray:
        """Hitung bobot dari data menggunakan Shannon Entropy."""
        X = df[self.cols].values.astype(float)
        self.weights = shannon_entropy_weights(X)
        return self.weights
        
    def set_weights(self, weights: np.ndarray | list[float]):
        """Set bobot secara manual."""
        w = np.array(weights, dtype=float)
        self.weights = w / w.sum()
        
    def evaluate(self, df: pd.DataFrame, weights: np.ndarray | None = None) -> pd.DataFrame:
        """
        Hitung skor dan ranking TOPSIS untuk DataFrame.
        """
        if weights is None:
            if self.weights is None:
                self.fit_entropy(df)
            weights = self.weights
        else:
            weights = np.array(weights) / np.sum(weights)
            
        X = df[self.cols].values.astype(float)
        C, D_pos, D_neg, A_pos, A_neg = topsis(X, weights, self.criteria_types)
        
        result_df = df.copy()
        result_df["skor_topsis"] = C
        result_df["D_pos"] = D_pos
        result_df["D_neg"] = D_neg
        result_df["rank_topsis"] = result_df["skor_topsis"].rank(ascending=False).astype(int)
        
        return result_df
