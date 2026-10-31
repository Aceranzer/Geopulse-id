// Peta choropleth dan tabel matriks pada halaman Ringkasan.
const WARNA = window.KLASTER_WARNA;
const norm = s => String(s).replace(/\s+/g, " ").trim().toUpperCase();
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const id = n => n.toLocaleString("id-ID", { maximumFractionDigits: 0 });

const KOLOM = [
  { key: "rank_topsis", label: "Rank", num: true, fmt: v => v },
  { key: "kecamatan", label: "Kecamatan", fmt: v => esc(v) },
  { key: "wilayah", label: "Kota", fmt: v => esc(v) },
  { key: "skor_topsis", label: "Skor TOPSIS", num: true, fmt: v => v.toFixed(3) },
  { key: "kejadian_per_tahun", label: "Frekuensi (kejadian/thn)", num: true, fmt: v => v.toFixed(1) },
  { key: "tinggi_max_cm", label: "Tinggi Air (cm)", num: true, fmt: v => id(v) },
  { key: "lama_hari_mean", label: "Durasi (hari)", num: true, fmt: v => v.toFixed(1) },
  { key: "jiwa_per_tahun", label: "Jiwa Terdampak (jiwa/thn)", num: true, fmt: v => id(v) },
  { key: "cluster_id", label: "Klaster", fmt: (v, r) => `<span class="pill c${v}">${esc(r.cluster_name)}</span>` },
];

let data = [], urut = { key: "rank_topsis", asc: true }, halaman = 1;

function buatPeta(geo) {
  const peta = L.map("peta", { scrollWheelZoom: false });
  const byKey = Object.fromEntries(data.map(r => [norm(r.kecamatan), r]));
  const layer = L.geoJSON(geo, {
    style: f => {
      const r = byKey[norm(f.properties.kecamatan)];
      return { fillColor: r ? WARNA[r.cluster_id] : "#cccccc", fillOpacity: 0.85, color: "#ffffff", weight: 1 };
    },
    onEachFeature: (f, l) => {
      const r = byKey[norm(f.properties.kecamatan)];
      if (r) l.bindTooltip(`<b>${esc(r.kecamatan)}</b><br>Skor ${r.skor_topsis.toFixed(3)} · ${esc(r.cluster_name)}`);
    },
  }).addTo(peta);
  peta.fitBounds(layer.getBounds());

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
    .map(r => "<tr>" + KOLOM.map(k => `<td class="${k.num ? "num" : ""}">${k.fmt(r[k.key], r)}</td>`).join("") + "</tr>").join("");

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

Promise.all([fetch("/api/kecamatan").then(r => r.json()), fetch("/api/geojson").then(r => r.json())])
  .then(([rows, geo]) => { data = rows; buatPeta(geo); mulaiTabel(); })
  .catch(() => { document.getElementById("peta").textContent = "Data gagal dimuat."; });
