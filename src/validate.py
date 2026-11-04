"""Aturan validasi data sebelum dihitung (galat = data ditolak, peringatan = hanya diberi tahu)."""

import numpy as np
import pandas as pd

from src.pipeline import CRIT_COLS, filter_kecamatan

N_KECAMATAN = 42
MIN_ANGGOTA_KLASTER = 5


def validate_master(master: pd.DataFrame, nama_geojson=None):
    """Mengembalikan daftar galat (kosong = lolos)."""
    kolom_hilang = [c for c in ["kecamatan", "wilayah"] + CRIT_COLS if c not in master.columns]
    if kolom_hilang:
        return [f"Kolom wajib tidak ada: {kolom_hilang}"]

    errors = []
    df = filter_kecamatan(master)
    if len(df) != N_KECAMATAN or df.kecamatan.nunique() != N_KECAMATAN:
        errors.append(f"Jumlah kecamatan harus tepat {N_KECAMATAN} (ditemukan {len(df)}, unik {df.kecamatan.nunique()}).")

    if nama_geojson is not None:
        beda = set(df.kecamatan) ^ set(nama_geojson)
        if beda:
            errors.append(f"Nama kecamatan tidak cocok dengan GeoJSON: {sorted(beda)}")

    for c in CRIT_COLS:
        num = pd.to_numeric(df[c], errors="coerce")
        if num.isna().any():
            errors.append(f"Kriteria '{c}' berisi nilai kosong/bukan angka: {df.kecamatan[num.isna()].tolist()}")
        elif not np.isfinite(num).all():
            errors.append(f"Kriteria '{c}' berisi nilai tak hingga.")
        elif (num < 0).any():
            errors.append(f"Kriteria '{c}' berisi nilai negatif: {df.kecamatan[num < 0].tolist()}")

    jp = pd.to_numeric(df["jiwa_per_1000"], errors="coerce")
    luar = (jp < 0) | (jp > 1000)
    if luar.any():
        errors.append(f"jiwa_per_1000 harus antara 0 dan 1000: {df.kecamatan[luar].tolist()}")
    return errors


def validate_result(clustered: pd.DataFrame):
    """Peringatan setelah klaster dihitung."""
    warnings = []
    ukuran = clustered.cluster_id.value_counts()
    kecil = ukuran[ukuran < MIN_ANGGOTA_KLASTER]
    if len(kecil):
        warnings.append(f"Klaster dengan anggota < {MIN_ANGGOTA_KLASTER}: {kecil.to_dict()}")
    return warnings
