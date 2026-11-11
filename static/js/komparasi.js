Chart.defaults.font.size = 14;
// Komparasi dua kecamatan: kartu ringkas, grafik nilai relatif, tabel nilai asli, panel tindakan.
const WARNA = window.KLASTER_WARNA, REK = window.REKOMENDASI;
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = v => Math.abs(v) >= 100 ? v.toLocaleString("id-ID", { maximumFractionDigits: 0 }) : v.toLocaleString("id-ID", { maximumFractionDigits: 2 });

let rows = [], kriteria = [], chart = null;
if (window.innerWidth < 700) document.addEventListener('DOMContentLoaded', () => { document.querySelector('.chart-box').style.height = '360px'; });
const selA = document.getElementById("selA"), selB = document.getElementById("selB");

// nilai relatif 0-1 (min-maks 42 kecamatan)
function relatif(kolom, v) {
  const nilai = rows.map(r => r[kolom]);
  const lo = Math.min(...nilai), hi = Math.max(...nilai);
  return hi === lo ? 0 : (v - lo) / (hi - lo);
}

function ringkas(r) {
  return `<div class="card">
    <div class="nama">${esc(r.kecamatan)}</div>
    <div class="muted">${esc(r.wilayah)}</div>
    <div class="angka"><span>Peringkat<b>#${r.rank_topsis}</b></span><span>Skor risiko<b>${r.skor_topsis.toFixed(3)}</b></span></div>
    <span class="pill c${r.cluster_id}">${esc(r.cluster_name)}</span>
    ${r.silhouette_sample < 0.1 ? '<div class="muted" style="margin-top:8px;">▲ Kecamatan batas: klaster kurang pasti</div>' : ""}
  </div>`;
}

function tindakan(r) {
  const daftar = REK[r.cluster_id];
  const isi = daftar
    ? `<ul class="tindakan">${daftar.map(t => `<li><span class="prio ${esc(t.prioritas)}">${esc(t.prioritas)}</span> ${esc(t.tindakan)}</li>`).join("")}</ul>`
    : '<div class="placeholder">Rekomendasi belum ditetapkan.</div>';
  return `<div><b>${esc(r.kecamatan)}</b> <span class="pill c${r.cluster_id}">${esc(r.cluster_name)}</span>${isi}</div>`;
}

function tampil() {
  const a = rows.find(r => r.kecamatan === selA.value), b = rows.find(r => r.kecamatan === selB.value);
  document.getElementById("hasil").style.display = a && b ? "block" : "none";
  document.getElementById("petunjuk").style.display = a && b ? "none" : "block";
  if (!a || !b) return;

  document.getElementById("ringkas").innerHTML = ringkas(a) + ringkas(b);
  document.getElementById("tindakan").innerHTML = tindakan(a) + tindakan(b);
  document.getElementById("thA").textContent = a.kecamatan;
  document.getElementById("thB").textContent = b.kecamatan;
  document.querySelector("#tabel-asli tbody").innerHTML = kriteria.map(c =>
    `<tr><td>${esc(c.desc)}</td><td>${esc(c.satuan)}</td><td class="num">${fmt(a[c.kolom])}</td><td class="num">${fmt(b[c.kolom])}</td></tr>`).join("");

  const data = {
    labels: kriteria.map(c => c.desc),
    datasets: [
      { label: a.kecamatan, data: kriteria.map(c => relatif(c.kolom, a[c.kolom])), backgroundColor: "#111111" },
      { label: b.kecamatan, data: kriteria.map(c => relatif(c.kolom, b[c.kolom])), backgroundColor: "#9a9a9a" },
    ],
  };
  if (chart) { chart.data = data; chart.update(); return; }
  chart = new Chart(document.getElementById("grafik"), {
    type: "bar", data,
    options: { indexAxis: "y", maintainAspectRatio: false, scales: { x: { min: 0, max: 1 } } },
  });
}

window.BobotAktif.muatData().then(hasil => {
  rows = hasil.kecamatan; kriteria = hasil.klaster.kriteria;
  const opsi = '<option value="">— pilih kecamatan —</option>' +
    [...rows].sort((x, y) => x.kecamatan.localeCompare(y.kecamatan)).map(r => `<option>${esc(r.kecamatan)}</option>`).join("");
  selA.innerHTML = selB.innerHTML = opsi;
  selA.addEventListener("change", tampil); selB.addEventListener("change", tampil);
  // tautan langsung: /komparasi?a=KEBON JERUK&b=TANAH ABANG
  const q = new URLSearchParams(location.search);
  if (q.get("a")) selA.value = q.get("a");
  if (q.get("b")) selB.value = q.get("b");
  tampil();
});
