// Peta choropleth dan tabel matriks pada halaman Ringkasan.
const WARNA = window.KLASTER_WARNA;
const norm = s => String(s).replace(/\s+/g, " ").trim().toUpperCase();
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const id = n => n.toLocaleString("id-ID", { maximumFractionDigits: 0 });

const KOLOM = [
  { key: "rank_topsis", label: "Peringkat", num: true, fmt: v => v },
  { key: "kecamatan", label: "Kecamatan", fmt: v => esc(v) },
  { key: "wilayah", label: "Kota", fmt: v => esc(v) },
  { key: "skor_topsis", label: "Skor risiko", num: true, fmt: v => v.toFixed(3) },
  { key: "kejadian_per_tahun", label: "Banjir (kali/thn)", num: true, fmt: v => v.toFixed(1) },
  { key: "tinggi_max_cm", label: "Tinggi air (cm)", num: true, fmt: v => id(v) },
  { key: "lama_hari_mean", label: "Durasi (hari)", num: true, fmt: v => v.toFixed(1) },
  { key: "jiwa_per_tahun", label: "Warga terdampak/thn", num: true, fmt: v => id(v) },
  { key: "cluster_id", label: "Klaster", fmt: (v, r) => `<span class="pill c${v}">${esc(r.cluster_name)}</span>` },
];

let data = [], urut = { key: "rank_topsis", asc: true }, halaman = 1;

function buatPeta(geo) {
  const peta = L.map("peta", { scrollWheelZoom: false, center: [-6.2088, 106.8456], zoom: 11 });
  const atribusi = "Basemap &amp; hillshade: Esri, HERE, Garmin, © OpenStreetMap contributors";

  // urutan lapisan: basemap -> hillshade -> choropleth
  L.tileLayer("https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}", { maxZoom: 16, attribution: atribusi }).addTo(peta);
  const hillshade = L.tileLayer("https://services.arcgisonline.com/arcgis/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}",
    { opacity: 0.45, maxZoom: 16 }).addTo(peta);

  const byKey = Object.fromEntries(data.map(r => [norm(r.kecamatan), r]));
  const klaster = L.geoJSON(geo, {
    style: f => {
      const r = byKey[norm(f.properties.kecamatan)];
      return { fillColor: r ? WARNA[r.cluster_id] : "#cccccc", fillOpacity: 0.6, color: "#ffffff", weight: 1 };
    },
    onEachFeature: (f, l) => {
      const r = byKey[norm(f.properties.kecamatan)];
      if (r) {
        l.bindTooltip(`<b>${esc(r.kecamatan)}</b><br>Skor ${r.skor_topsis.toFixed(3)} · ${esc(r.cluster_name)}`);
        l.on("click", () => bukaDetail(r.slug));         // klik poligon = buka panel detail
      }
    },
  }).addTo(peta);

  L.control.layers(null, { "Topografi (hillshade)": hillshade, "Klaster prioritas": klaster }, { collapsed: false }).addTo(peta);

  const legendaTopo = L.control({ position: "bottomright" });
  legendaTopo.onAdd = () => {
    const d = L.DomUtil.create("div", "legenda-topo");
    d.innerHTML = '<div class="bar"></div><div class="teks"><span>Dataran rendah</span><span>Dataran tinggi</span></div>';
    return d;
  };
  legendaTopo.addTo(peta);
  // legenda ikut tampil/hilang bersama lapisan hillshade
  peta.on("overlayremove", e => { if (e.layer === hillshade) legendaTopo.getContainer().style.display = "none"; });
  peta.on("overlayadd", e => { if (e.layer === hillshade) legendaTopo.getContainer().style.display = ""; });

  const nama = {};
  data.forEach(r => nama[r.cluster_id] = r.cluster_name);
  document.getElementById("legend").innerHTML = Object.keys(nama).sort()
    .map(i => `<span><i style="background:${WARNA[i]}"></i>${i} · ${esc(nama[i])}</span>`).join("");
}

function tampilTabel() {
  const q = document.getElementById("cari").value.trim().toLowerCase();
  const per = +document.getElementById("jumlah").value;
  let rows = data.filter(r => !q || (r.kecamatan + " " + r.wilayah).toLowerCase().includes(q));
  rows.sort((a, b) => {
    const x = a[urut.key], y = b[urut.key];
    const c = typeof x === "string" ? x.localeCompare(y) : x - y;
    return urut.asc ? c : -c;
  });
  const total = Math.max(1, Math.ceil(rows.length / per));
  halaman = Math.min(halaman, total);
  const mulai = (halaman - 1) * per;

  document.querySelector("#tabel tbody").innerHTML = rows.slice(mulai, mulai + per)
    .map(r => `<tr data-slug="${esc(r.slug)}" tabindex="0" class="klik" title="Klik untuk detail">` + KOLOM.map(k => `<td class="${k.num ? "num" : ""}">${k.fmt(r[k.key], r)}</td>`).join("") + "</tr>").join("");

  let pager = `<span>${rows.length} kecamatan</span>`;
  for (let p = 1; p <= total; p++) pager += `<a href="#" class="page ${p === halaman ? "active" : ""}" data-p="${p}" style="text-decoration:none">${p}</a>`;
  document.getElementById("pager").innerHTML = pager;
}

function mulaiTabel() {
  document.getElementById("thead").innerHTML = KOLOM.map(k =>
    `<th class="sortable ${k.num ? "num" : ""}" data-key="${k.key}">${k.label}</th>`).join("");
  document.getElementById("thead").addEventListener("click", e => {
    const key = e.target.dataset.key;
    if (!key) return;
    urut = { key, asc: urut.key === key ? !urut.asc : true };
    tampilTabel();
  });
  document.getElementById("pager").addEventListener("click", e => {
    if (e.target.dataset.p) { e.preventDefault(); halaman = +e.target.dataset.p; tampilTabel(); }
  });
  document.getElementById("cari").addEventListener("input", () => { halaman = 1; tampilTabel(); });
  document.getElementById("jumlah").addEventListener("change", () => { halaman = 1; tampilTabel(); });
  tampilTabel();
}

// KPI dan tiga teratas mengikuti bobot aktif (saat bobot bawaan, isinya sama dengan yang dirender server)
function perbaruiRingkasan() {
  const urut3 = [...data].sort((a, b) => a.rank_topsis - b.rank_topsis);
  document.getElementById("kpi-prioritas").textContent = data.filter(r => r.cluster_id === 0).length;
  const skor = data.map(r => r.skor_topsis);
  document.getElementById("kpi-skor").textContent = `${Math.min(...skor).toFixed(2)} – ${Math.max(...skor).toFixed(2)}`;
  const judul = s => String(s).toLowerCase().replace(/(^|\s)\S/g, c => c.toUpperCase());
  document.getElementById("top3").innerHTML = urut3.slice(0, 3).map(r => `
    <div class="rank-row klik" data-slug="${esc(r.slug)}" tabindex="0">
      <span class="no">#${r.rank_topsis}</span>
      <span class="name"><b>${esc(judul(r.kecamatan))}</b> · ${esc(judul(r.wilayah))}<br>
        ${r.kejadian_per_tahun.toFixed(1)} kali banjir/tahun · air maks ${Math.trunc(r.tinggi_max_cm)} cm · skor ${r.skor_topsis.toFixed(3)}</span>
      <span class="pill c${r.cluster_id}">${esc(r.cluster_name)}</span>
    </div>`).join("");
}

Promise.all([window.BobotAktif.muatData(), fetch("/api/geojson").then(r => r.json())])
  .then(([hasil, geo]) => {
    data = hasil.kecamatan; buatPeta(geo); mulaiTabel(); perbaruiRingkasan();
    const awal = new URLSearchParams(location.search).get("detail");     // tautan langsung: /?detail=kebon-jeruk
    if (awal) bukaDetail(awal);
  })
  .catch(() => { document.getElementById("peta").textContent = "Data gagal dimuat."; });

// saat dicetak, tampilkan seluruh baris tabel lalu kembalikan pilihan semula
let jumlahSebelumCetak = null;
window.addEventListener("beforeprint", () => {
  const sel = document.getElementById("jumlah");
  jumlahSebelumCetak = sel.value; sel.value = "50"; halaman = 1; tampilTabel();
});
window.addEventListener("afterprint", () => {
  if (jumlahSebelumCetak) { document.getElementById("jumlah").value = jumlahSebelumCetak; halaman = 1; tampilTabel(); }
});

// ---- panel detail kecamatan ----
const dlg = document.getElementById("detail");
const nilaiId = v => (Math.abs(v) >= 100 ? v.toLocaleString("id-ID", { maximumFractionDigits: 0 }) : v.toLocaleString("id-ID", { maximumFractionDigits: 2 }));

function bukaDetail(slug) {
  const r = data.find(d => d.slug === slug);
  if (!r) return;
  const tindakan = window.REKOMENDASI[r.cluster_id];
  document.getElementById("detail-isi").innerHTML = `
    <h2 style="margin:0">${esc(r.kecamatan)}</h2>
    <div class="muted">${esc(r.wilayah)}</div>
    <div class="detail-ringkas">
      <div><span class="muted">Peringkat</span><b>#${r.rank_topsis} dari ${data.length}</b></div>
      <div><span class="muted">Skor risiko</span><b>${r.skor_topsis.toFixed(3)}</b></div>
      <div><span class="muted">Klaster</span><b><span class="pill c${r.cluster_id}">${esc(r.cluster_name)}</span></b></div>
    </div>
    ${r.silhouette_sample < 0.1 ? '<div class="muted">▲ Kecamatan batas: klaster kurang pasti</div>' : ""}
    <h3>Kriteria</h3>
    <table class="table"><tbody>${window.KRITERIA.map(k =>
      `<tr><td>${esc(k.desc)}</td><td class="muted">${esc(k.satuan)}</td><td class="num">${nilaiId(r[k.kolom])}</td></tr>`).join("")}</tbody></table>
    <h3>Prioritas tindakan</h3>
    ${tindakan ? `<ul>${tindakan.map(t => `<li>${esc(t.tindakan)} <span class="muted">(prioritas ${esc(t.prioritas)})</span></li>`).join("")}</ul>`
               : '<div class="placeholder">Rekomendasi belum ditetapkan.</div>'}
    <div class="muted" style="margin-top:6px">${esc(window.CATATAN)}</div>
    <div style="margin-top:14px"><a class="btn" href="/ekspor/kecamatan/${esc(r.slug)}.pdf${window.BobotAktif.queryPdf()}">Unduh profil (PDF)</a></div>`;
  dlg.showModal();
}

document.querySelector("#tabel tbody").addEventListener("click", e => {
  const tr = e.target.closest("tr[data-slug]");
  if (tr) bukaDetail(tr.dataset.slug);
});
document.querySelector("#tabel tbody").addEventListener("keydown", e => {
  if (e.key === "Enter" && e.target.dataset.slug) bukaDetail(e.target.dataset.slug);
});
document.getElementById("top3").addEventListener("click", e => {
  const el = e.target.closest("[data-slug]");
  if (el) bukaDetail(el.dataset.slug);
});
document.getElementById("detail-tutup").addEventListener("click", () => dlg.close());
dlg.addEventListener("click", e => { if (e.target === dlg) dlg.close(); });   // klik latar = tutup
