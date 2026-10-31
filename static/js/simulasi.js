// Simulasi bobot: hitung ulang TOPSIS di browser dan tampilkan pergeseran peringkat.
const { topsis, rankDesc, normalisasi } = window.TopsisJS;
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const NAMA_PRESET = { entropi: "Entropi (bawaan)", sama: "Sama rata", pakar: "Pakar", kustom: "Kustom" };
let kriteria, bobot, X, baris, mode = "entropi", raw = [];
const slidersEl = document.getElementById("sliders");

function bobotAktif() {
  return mode === "kustom" ? normalisasi(raw) : bobot[mode];
}

function gambarSlider() {
  const w = bobotAktif();
  slidersEl.innerHTML = kriteria.map((c, j) => `
    <div class="slider-row">
      <label for="s${j}">${esc(c.desc)}${c.type === "cost" ? " (cost)" : ""}<span class="muted"> · ${esc(c.dimensi)}</span></label>
      <input type="range" id="s${j}" min="0" max="100" step="0.5" value="${(mode === "kustom" ? raw[j] : w[j] * 100).toFixed(1)}" ${mode === "kustom" ? "" : "disabled"}>
      <b id="p${j}">${(w[j] * 100).toFixed(1)}%</b>
    </div>`).join("");
  if (mode === "kustom") kriteria.forEach((c, j) => document.getElementById("s" + j).addEventListener("input", e => {
    raw[j] = +e.target.value; perbaruiPersen(); hitung();
  }));
}

function perbaruiPersen() {
  normalisasi(raw).forEach((v, j) => document.getElementById("p" + j).textContent = (v * 100).toFixed(1) + "%");
}

function hitung() {
  const skor = topsis(X, bobotAktif(), kriteria.map(c => c.type));
  const rank = rankDesc(skor);
  const hasil = baris.map((b, i) => ({ ...b, skorBaru: skor[i], rankBaru: rank[i], delta: b.rank_topsis - rank[i] }));
  hasil.sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta) || a.rankBaru - b.rankBaru);

  const berubah = hasil.filter(h => h.delta !== 0).length;
  const top10Lama = new Set(hasil.filter(h => h.rank_topsis <= 10).map(h => h.kecamatan));
  const top10Sama = hasil.filter(h => h.rankBaru <= 10 && top10Lama.has(h.kecamatan)).length;
  document.getElementById("ringkasan").innerHTML =
    `<b>${NAMA_PRESET[mode]}</b>: ${berubah} dari ${hasil.length} kecamatan berpindah peringkat; ${top10Sama} dari 10 kecamatan teratas bawaan tetap di 10 besar.`;

  document.querySelector("#tabel tbody").innerHTML = hasil.map(h => {
    const panah = h.delta > 0 ? `<span class="naik">▲ naik ${h.delta}</span>` : h.delta < 0 ? `<span class="turun">▼ turun ${-h.delta}</span>` : '<span class="muted">– tetap</span>';
    return `<tr><td>${esc(h.kecamatan)}</td><td>${esc(h.wilayah)}</td><td class="num">${h.rank_topsis}</td><td class="num">${h.rankBaru}</td><td class="num">${h.skorBaru.toFixed(3)}</td><td>${panah}</td></tr>`;
  }).join("");
}

function pilihMode(m) {
  if (m === "kustom" && !raw.length) raw = bobot[mode].map(v => v * 100);   // mulai dari preset yang sedang dipilih
  mode = m;
  document.querySelectorAll(".preset").forEach(b => b.classList.toggle("aktif", b.dataset.mode === m));
  gambarSlider(); hitung();
}

Promise.all([fetch("/api/kriteria").then(r => r.json()), fetch("/api/kecamatan").then(r => r.json())]).then(([kr, kec]) => {
  kriteria = kr.kriteria; bobot = kr.bobot;
  const info = Object.fromEntries(kec.map(k => [k.kecamatan, k]));
  X = kr.data.map(d => kriteria.map(c => d[c.kolom]));
  baris = kr.data.map(d => ({ kecamatan: d.kecamatan, wilayah: info[d.kecamatan].wilayah, rank_topsis: info[d.kecamatan].rank_topsis }));

  // pemeriksaan: hasil JS dengan bobot entropi harus sama dengan skor di topsis_result.csv
  const skor = topsis(X, bobot.entropi, kriteria.map(c => c.type));
  const selisih = Math.max(...kr.data.map((d, i) => Math.abs(skor[i] - info[d.kecamatan].skor_topsis)));
  document.getElementById("verifikasi").textContent = selisih < 1e-6
    ? `Verifikasi: perhitungan di browser sama dengan topsis_result.csv (selisih skor maksimum ${selisih.toExponential(1)}).`
    : `Peringatan: perhitungan di browser berbeda dari topsis_result.csv (selisih ${selisih.toExponential(1)}).`;

  document.querySelectorAll(".preset").forEach(b => b.addEventListener("click", () => pilihMode(b.dataset.mode)));
  // tautan langsung: /simulasi?mode=pakar
  const awal = new URLSearchParams(location.search).get("mode");
  pilihMode(NAMA_PRESET[awal] ? awal : "entropi");
});
