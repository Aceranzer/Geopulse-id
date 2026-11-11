Chart.defaults.font.size = 14;
// Kartu klaster dan grafik pemilihan k pada halaman Klaster.
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = v => Math.abs(v) >= 100 ? v.toLocaleString("id-ID", { maximumFractionDigits: 0 }) : v.toLocaleString("id-ID", { maximumFractionDigits: 2 });

function kartu(k, rataSemua, kriteria) {
  const baris = kriteria.map(c => {
    const a = k.rata[c.kolom], b = rataSemua[c.kolom];
    const lebihTinggi = a > b;
    // untuk kriteria cost (alat dini) nilai lebih rendah = lebih berisiko
    const berisiko = c.type === "cost" ? !lebihTinggi : lebihTinggi;
    const panah = Math.abs(a - b) < 1e-9 ? "" : `<span class="${berisiko ? "naik" : "turun"}">${lebihTinggi ? "▲" : "▼"}</span>`;
    return `<tr><td>${esc(c.desc)} <span class="muted">(${esc(c.satuan)})</span></td><td>${fmt(a)} ${panah}</td><td>${fmt(b)}</td></tr>`;
  }).join("");

  const anggota = k.anggota.sort((x, y) => x.rank - y.rank).map(m =>
    `<li>${m.batas ? `<span class="batas" title="Kecamatan batas: silhouette ${m.silhouette.toFixed(2)}">▲</span> ` : ""}#${m.rank} ${esc(m.kecamatan)}${m.batas ? ' <span class="muted">(kurang pasti)</span>' : ""}</li>`).join("");

  return `<div class="card klaster-card" style="border-left-color:${k.warna}">
    <div class="head"><h3><span class="pill c${k.cluster_id}">${k.cluster_id} · ${esc(k.nama)}</span></h3><span class="n">${k.n} <span class="muted">kecamatan</span></span></div>
    <div class="muted">Skor risiko rata-rata ${k.rata.skor_topsis.toFixed(3)} (semua ${rataSemua.skor_topsis.toFixed(3)})</div>
    <table class="table mini" style="margin-top:8px;"><thead><tr><th>Rata-rata kriteria</th><th>Klaster</th><th>Semua</th></tr></thead><tbody>${baris}</tbody></table>
    <ul class="anggota">${anggota}</ul>
  </div>`;
}

function grafik(id, label, nilai, ks, kFinal, warna) {
  new Chart(document.getElementById(id), {
    type: "line",
    data: { labels: ks, datasets: [{ label, data: nilai, borderColor: warna, backgroundColor: warna, tension: 0.2,
      pointRadius: ks.map(k => k === kFinal ? 8 : 4), pointBackgroundColor: ks.map(k => k === kFinal ? "#8b0000" : warna) }] },
    options: { maintainAspectRatio: false, plugins: { legend: { display: false } },
      scales: { x: { title: { display: true, text: "k (jumlah klaster)" } } } },
  });
}

window.BobotAktif.muatData().then(hasil => {
  const d = { ...hasil.klaster };
  document.getElementById("kartu").innerHTML = d.klaster.map(k => kartu(k, d.rata_semua, d.kriteria)).join("");
  document.getElementById("status-bobot").textContent = hasil.aktif
    ? `Klaster di bawah mengikuti bobot aktif (${window.BobotAktif.NAMA[hasil.preset]}).`
    : "Klaster di bawah memakai bobot bawaan (entropi).";
  grafikPemilihanK({ sweep: hasil.sweep, k_final: hasil.k_final });
});

function grafikPemilihanK(d) {
  const ks = d.sweep.map(r => r.k);
  grafik("elbow", "Inertia", d.sweep.map(r => r.inertia), ks, d.k_final, "#555555");
  grafik("sil", "Silhouette", d.sweep.map(r => r.silhouette), ks, d.k_final, "#555555");
  const sil = Object.fromEntries(d.sweep.map(r => [r.k, r.silhouette]));
  const rentang = Math.max(...Object.values(sil)) - Math.min(...Object.values(sil));
  document.getElementById("catatan-k").textContent =
    `Titik merah: k = ${d.k_final} (silhouette ${sil[d.k_final].toFixed(3)}). Nilainya hampir sama untuk semua k (selisih ${rentang.toFixed(3)}), ` +
    `jadi k = ${d.k_final} dipilih agar mudah dibaca: empat tingkat prioritas.`;
}
