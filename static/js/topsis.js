// TOPSIS di browser; langkah-langkahnya sama dengan src/topsis.py.
// X: array baris (alternatif) x kolom (kriteria); w: bobot (jumlah 1); types: "benefit" | "cost".
(function (root) {
  const EPS = 1e-12;

  function topsis(X, w, types) {
    const m = X.length, n = w.length;
    // 1. normalisasi vektor dan pembobotan
    const norm = Array.from({ length: n }, (_, j) => Math.sqrt(X.reduce((s, r) => s + r[j] * r[j], 0)));
    const V = X.map(r => r.map((x, j) => (x / (norm[j] + EPS)) * w[j]));
    // 2. solusi ideal positif dan negatif
    const aPos = [], aNeg = [];
    for (let j = 0; j < n; j++) {
      const kol = V.map(r => r[j]), lo = Math.min(...kol), hi = Math.max(...kol);
      aPos.push(types[j] === "benefit" ? hi : lo);
      aNeg.push(types[j] === "benefit" ? lo : hi);
    }
    // 3. jarak ke solusi ideal dan kedekatan relatif
    return V.map(r => {
      const dPos = Math.sqrt(r.reduce((s, v, j) => s + (v - aPos[j]) ** 2, 0));
      const dNeg = Math.sqrt(r.reduce((s, v, j) => s + (v - aNeg[j]) ** 2, 0));
      return dNeg / (dPos + dNeg + EPS);
    });
  }

  // peringkat 1 = skor tertinggi; skor kembar dapat rata-rata lalu dibulatkan ke bawah (sama dengan pandas rank().astype(int))
  function rankDesc(scores) {
    const idx = scores.map((s, i) => i).sort((a, b) => scores[b] - scores[a]);
    const rank = new Array(scores.length);
    let i = 0;
    while (i < idx.length) {
      let j = i;
      while (j + 1 < idx.length && scores[idx[j + 1]] === scores[idx[i]]) j++;
      const avg = (i + 1 + j + 1) / 2;
      for (let k = i; k <= j; k++) rank[idx[k]] = Math.floor(avg);
      i = j + 1;
    }
    return rank;
  }

  // bobot mentah (mis. nilai slider) -> bobot yang berjumlah 1; semua nol dianggap sama rata
  function normalisasi(raw) {
    const total = raw.reduce((s, v) => s + v, 0);
    return total > 0 ? raw.map(v => v / total) : raw.map(() => 1 / raw.length);
  }

  const api = { topsis, rankDesc, normalisasi };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.TopsisJS = api;
})(typeof window !== "undefined" ? window : globalThis);
