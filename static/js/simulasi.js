// Simulasi bobot: bobot dikirim ke server (POST /api/simulasi), tabel pergeseran peringkat dari balasan server.
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const NAMA_PRESET = { entropi: "Entropi (bawaan)", sama: "Sama rata", pakar: "Pakar", kustom: "Kustom" };
let kriteria, bobot, mode = "entropi", raw = [], timer = null, urutan = 0;
const slidersEl = document.getElementById("sliders");

// bobot mentah (nilai slider) -> berjumlah 1; hanya untuk label persen, server menormalisasi sendiri
function normalisasi(r) {
  const total = r.reduce((s, v) => s + v, 0);
  return total > 0 ? r.map(v => v / total) : r.map(() => 1 / r.length);
}

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
    raw[j] = +e.target.value; perbaruiPersen(); hitungTertunda();
  }));
}

function perbaruiPersen() {
  normalisasi(raw).forEach((v, j) => document.getElementById("p" + j).textContent = (v * 100).toFixed(1) + "%");
}

function hitungTertunda() {            // debounce 300 ms saat slider digeser
  clearTimeout(timer);
  timer = setTimeout(hitung, 300);
}

function tampilkan(hasil) {
  const berubah = hasil.filter(h => h.delta !== 0).length;
  const top10Sama = hasil.filter(h => h.rank_baru <= 10 && h.rank_bawaan <= 10).length;
  document.getElementById("ringkasan").innerHTML =
    `<b>${NAMA_PRESET[mode]}</b>: ${berubah} dari ${hasil.length} kecamatan berpindah peringkat; ${top10Sama} dari 10 kecamatan teratas bawaan tetap di 10 besar.`;

  document.querySelector("#tabel tbody").innerHTML = hasil.map(h => {
    const panah = h.delta > 0 ? `<span class="naik">▲ naik ${h.delta}</span>` : h.delta < 0 ? `<span class="turun">▼ turun ${-h.delta}</span>` : '<span class="muted">– tetap</span>';
    return `<tr><td>${esc(h.kecamatan)}</td><td>${esc(h.wilayah)}</td><td class="num">${h.rank_bawaan}</td><td class="num">${h.rank_baru}</td><td class="num">${h.skor_baru.toFixed(3)}</td><td>${panah}</td></tr>`;
  }).join("");
}

function hitung() {
  const saya = ++urutan;               // abaikan balasan lama jika ada permintaan yang lebih baru
  fetch("/api/simulasi", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ preset: mode, bobot: bobotAktif() }),
  })
    .then(r => r.json().then(d => ({ ok: r.ok, d })))
    .then(({ ok, d }) => {
      if (saya !== urutan) return;
      if (!ok) { document.getElementById("ringkasan").textContent = d.galat || "Perhitungan gagal."; return; }
      tampilkan(d.hasil);
    })
    .catch(() => { if (saya === urutan) document.getElementById("ringkasan").textContent = "Server tidak dapat dihubungi."; });
}

function pilihMode(m) {
  if (m === "kustom" && !raw.length) raw = bobot[mode].map(v => v * 100);   // mulai dari preset yang sedang dipilih
  mode = m;
  document.querySelectorAll(".preset").forEach(b => b.classList.toggle("aktif", b.dataset.mode === m));
  gambarSlider(); hitung();
}

fetch("/api/kriteria").then(r => r.json()).then(kr => {
  kriteria = kr.kriteria; bobot = kr.bobot;
  document.querySelectorAll(".preset").forEach(b => b.addEventListener("click", () => pilihMode(b.dataset.mode)));
  // tautan langsung: /simulasi?mode=pakar
  const awal = new URLSearchParams(location.search).get("mode");
  pilihMode(NAMA_PRESET[awal] ? awal : "entropi");
});
