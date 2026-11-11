// Simulasi bobot: pratinjau lewat POST /api/pipeline (server menghitung TOPSIS + klaster); "Terapkan ke Dashboard"
// menyimpan bobot di sessionStorage sehingga halaman lain ikut memakainya.
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const NAMA_PRESET = window.BobotAktif.NAMA;
let kriteria, bobot, mode = "entropi", raw = [], timer = null, urutan = 0;
const slidersEl = document.getElementById("sliders");
const info = document.getElementById("ringkasan");

// bobot mentah (nilai slider) -> berjumlah 1; hanya untuk label persen, server menormalisasi sendiri
function normalisasi(r) {
  const total = r.reduce((s, v) => s + v, 0);
  return total > 0 ? r.map(v => v / total) : r.map(() => 1 / r.length);
}

function bobotSekarang() {
  return mode === "kustom" ? normalisasi(raw) : bobot[mode];
}

// tombol PDF hanya relevan bila bobot berbeda dari bawaan (entropi)
function sama(a, b) { return a.every((v, i) => Math.abs(v - b[i]) < 1e-6); }
function perbaruiTombol() {
  document.getElementById("form-pdf").hidden = sama(bobotSekarang(), bobot.entropi);
}

function gambarSlider() {
  const w = bobotSekarang();
  slidersEl.innerHTML = kriteria.map((c, j) => `
    <div class="slider-row">
      <label for="s${j}">${esc(c.desc)}<span class="muted"> · ${esc(c.dimensi)}</span></label>
      <input type="range" id="s${j}" min="0" max="100" step="0.5" value="${(mode === "kustom" ? raw[j] : w[j] * 100).toFixed(1)}" ${mode === "kustom" ? "" : "disabled"}>
      <b id="p${j}">${(w[j] * 100).toFixed(1)}%</b>
    </div>`).join("");
  if (mode === "kustom") kriteria.forEach((c, j) => document.getElementById("s" + j).addEventListener("input", e => {
    raw[j] = +e.target.value; perbaruiPersen(); perbaruiTombol(); hitungTertunda();
  }));
}

function perbaruiPersen() {
  normalisasi(raw).forEach((v, j) => document.getElementById("p" + j).textContent = (v * 100).toFixed(1) + "%");
}

function hitungTertunda() {            // debounce 400 ms saat slider digeser
  info.textContent = "Menghitung…";
  clearTimeout(timer);
  timer = setTimeout(hitung, 400);
}

function tampilkan(rows) {
  const berubah = rows.filter(h => h.delta !== 0).length;
  const top10Sama = rows.filter(h => h.rank_topsis <= 10 && h.rank_bawaan <= 10).length;
  info.innerHTML = `<b>${NAMA_PRESET[mode]}</b>: ${berubah} kecamatan berubah peringkat · ${top10Sama} dari 10 teratas bawaan tetap di 10 besar.`;

  const urut = [...rows].sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta) || a.rank_topsis - b.rank_topsis);
  document.querySelector("#tabel tbody").innerHTML = urut.map(h => {
    const panah = h.delta > 0 ? `<span class="naik">▲ naik ${h.delta}</span>` : h.delta < 0 ? `<span class="turun">▼ turun ${-h.delta}</span>` : '<span class="muted">– tetap</span>';
    return `<tr><td>${esc(h.kecamatan)}</td><td>${esc(h.wilayah)}</td><td class="num">${h.rank_bawaan}</td><td class="num">${h.rank_topsis}</td><td class="num">${h.skor_topsis.toFixed(3)}</td><td>${panah}</td></tr>`;
  }).join("");
}

function hitung() {
  const saya = ++urutan;               // abaikan balasan lama jika ada permintaan yang lebih baru
  info.textContent = "Menghitung…";
  fetch("/api/pipeline", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ preset: mode, bobot: bobotSekarang() }),
  })
    .then(r => r.json().then(d => ({ ok: r.ok, d })))
    .then(({ ok, d }) => {
      if (saya !== urutan) return;
      if (!ok) { info.textContent = d.galat || "Perhitungan gagal."; return; }
      tampilkan(d.kecamatan);
    })
    .catch(() => { if (saya === urutan) info.textContent = "Server tidak dapat dihubungi."; });
}

let timerToast = null;
function toast(html) {
  const t = document.getElementById("toast");
  t.innerHTML = html; t.hidden = false;
  clearTimeout(timerToast);
  timerToast = setTimeout(() => { t.hidden = true; }, 7000);
}

// "Terapkan ke Dashboard": simpan bobot untuk sesi tab ini; bobot entropi (bawaan) berarti menghapus bobot aktif
document.getElementById("btn-terapkan").addEventListener("click", () => {
  window.BobotAktif.set(mode, bobotSekarang());
  window.BobotAktif.pasangBanner();
  toast(`Diterapkan: <b>${esc(NAMA_PRESET[mode])}</b>. Buka Dashboard untuk melihat efek pada peta &amp; peringkat. <a href="/">Buka Dashboard</a>`);
});

// tombol PDF mengirim bobot yang sedang dipratinjau ke server
document.getElementById("form-pdf").addEventListener("submit", () => {
  document.getElementById("payload-pdf").value = JSON.stringify({ preset: mode, bobot: bobotSekarang() });
});

function pilihMode(m) {
  if (m === "kustom" && !raw.length) raw = bobotSekarang().map(v => v * 100);   // mulai dari preset yang sedang dipilih
  mode = m;
  document.querySelectorAll(".preset").forEach(b => b.classList.toggle("aktif", b.dataset.mode === m));
  gambarSlider(); perbaruiTombol(); hitung();
}

fetch("/api/kriteria").then(r => r.json()).then(kr => {
  kriteria = kr.kriteria; bobot = kr.bobot;
  document.querySelectorAll(".preset").forEach(b => b.addEventListener("click", () => pilihMode(b.dataset.mode)));

  // urutan prioritas: ?mode=... di tautan, lalu bobot aktif sesi ini, lalu bawaan
  const awalUrl = new URLSearchParams(location.search).get("mode");
  const aktif = window.BobotAktif.get();
  if (!NAMA_PRESET[awalUrl] && aktif) {
    if (aktif.preset === "kustom") raw = aktif.bobot.map(v => v * 100);
    pilihMode(aktif.preset);
  } else {
    pilihMode(NAMA_PRESET[awalUrl] ? awalUrl : "entropi");
  }
});
