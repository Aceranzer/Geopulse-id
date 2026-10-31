"""Konfigurasi aplikasi. Rahasia hanya dibaca dari environment variable, tidak ditulis di repo."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"

TOPSIS_CSV = DATA_DIR / "topsis_result.csv"
CLUSTERED_CSV = DATA_DIR / "clustered_result.csv"
SWEEP_CSV = DATA_DIR / "k_sweep.csv"
GEOJSON = DATA_DIR / "kecamatan_poly.geojson"
METRICS_JSON = DATA_DIR / "metrics.json"

SECRET_KEY = os.environ.get("SECRET_KEY", "")            # wajib diisi di produksi
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")    # kosong = halaman admin dinonaktifkan
