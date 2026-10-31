"""Uji TOPSIS JavaScript (static/js/topsis.js) terhadap topsis_result.csv dan versi Python.

Butuh Node.js. Jalankan dari akar repo:  python -m tests.test_topsis_js
"""

import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

import config
from app import app
from src.pipeline import CRIT_COLS, CRIT_TYPES, W_EXPERT
from src.topsis import topsis

ROOT = Path(__file__).resolve().parent.parent

JS = """
const T = require(process.argv[1]);
const d = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const out = {};
for (const [nama, w] of Object.entries(d.bobot)) {
  const s = T.topsis(d.X, w, d.tipe);
  out[nama] = { skor: s, rank: T.rankDesc(s) };
}
out.kustom = { skor: T.topsis(d.X, T.normalisasi(d.kustom), d.tipe) };
console.log(JSON.stringify(out));
"""


def main():
    t = pd.read_csv(config.TOPSIS_CSV)
    kr = app.test_client().get("/api/kriteria").get_json()
    X = np.array([[row[c] for c in CRIT_COLS] for row in kr["data"]], dtype=float)
    kustom = [30, 0, 5, 10, 10, 25, 10, 10]          # slider mentah, jumlah bukan 100
    payload = {"X": X.tolist(), "tipe": CRIT_TYPES, "bobot": kr["bobot"], "kustom": kustom}

    proc = subprocess.run(["node", "-e", JS, str(ROOT / "static" / "js" / "topsis.js")],
                          input=json.dumps(payload), capture_output=True, text=True, check=True)
    js = json.loads(proc.stdout)

    # 1. bobot entropi di JS = topsis_result.csv
    selisih = np.abs(np.array(js["entropi"]["skor"]) - t.skor_topsis.values).max()
    print(f"entropi : selisih skor JS vs topsis_result.csv = {selisih:.2e}")
    assert selisih < 1e-6
    assert (np.array(js["entropi"]["rank"]) == t.rank_topsis.values).all(), "peringkat JS berbeda"

    # 2. bobot sama dan pakar = kolom skor_equal / skor_expert di CSV
    for nama, kolom in [("sama", "skor_equal"), ("pakar", "skor_expert")]:
        s = np.abs(np.array(js[nama]["skor"]) - t[kolom].values).max()
        print(f"{nama:8s}: selisih skor JS vs {kolom} = {s:.2e}")
        assert s < 1e-6
    assert np.allclose(kr["bobot"]["pakar"], W_EXPERT)

    # 3. bobot kustom: JS = Python dengan bobot yang dinormalisasi
    w = np.array(kustom, dtype=float) / sum(kustom)
    py = topsis(X, w, CRIT_TYPES)[0]
    s = np.abs(np.array(js["kustom"]["skor"]) - py).max()
    print(f"kustom  : selisih skor JS vs Python = {s:.2e}")
    assert s < 1e-9
    print("LULUS")


if __name__ == "__main__":
    main()
