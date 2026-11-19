// Peta choropleth dan tabel matriks pada halaman Ringkasan.
const WARNA = window.KLASTER_WARNA;
const norm = s => String(s).replace(/\s+/g, " ").trim().toUpperCase();
const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const id = n => n.toLocaleString("id-ID", { maximumFractionDigits: 0 });

const KOLOM = [
  { key: "rank_topsis", label: "Peringkat", num: true, fmt: v => v },
  { key: "kecamatan", label: "Kecamatan", fmt: v => esc(v) },
  { key: "wilayah", label: "Kota", fmt: v => `<span style="white-space:nowrap">${esc(v)}</span>` },
  { key: "skor_topsis", label: "Skor risiko", num: true, fmt: (v, r) => `<span class="skor-cell"><span class="bar" aria-hidden="true"><i class="fill-c${r.cluster_id}" style="width:${Math.round(v * 100)}%"></i></span>${v.toFixed(3)}</span>` },
  { key: "kejadian_per_tahun", label: "Banjir/thn", num: true, fmt: v => v.toFixed(1) },
  { key: "tinggi_max_cm", label: "Tinggi air (cm)", num: true, fmt: v => id(v) },
  { key: "lama_hari_mean", label: "Durasi (hari)", num: true, fmt: v => v.toFixed(1) },
  { key: "jiwa_per_tahun", label: "Warga terdampak", num: true, fmt: v => id(v) },
  { key: "cluster_id", label: "Klaster", fmt: (v, r) => `<span class="pill c${v}">${esc(r.cluster_name)}</span>` },
];

let data = [], urut = { key: "rank_topsis", asc: true }, halaman = 1;

function buatPeta(geo) {
  const peta = L.map("peta", { scrollWheelZoom: false, center: [-6.2088, 106.8456], zoom: 11 });
  const esri = "Esri, Maxar, Earthstar Geographics, HERE, Garmin";
  const LK = window.LapisanKetinggian;
  const atribusiDem = "Ketinggian: AWS Terrain Tiles (SRTM)";

  // peta dasar: satelit (bawaan, paling realistis), ketinggian berwarna, topografi, atau abu-abu polos
  const dasar = {
    "Satelit": L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      { maxZoom: 18, attribution: "Citra: " + esri }),
    "Ketinggian (tinggi/rendah)": LK.warna({ attribution: atribusiDem }),
    "Topografi jalan": L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
      { maxZoom: 17, subdomains: "abc", attribution: "© OpenStreetMap contributors, SRTM · © OpenTopoMap (CC-BY-SA)" }),
    "Abu-abu polos": L.tileLayer("https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
      { maxZoom: 16, attribution: "Basemap: " + esri + ", © OpenStreetMap contributors" }),
  };
  dasar["Satelit"].addTo(peta);
  // garis kontur digambar di atas warna klaster supaya tetap terlihat
  peta.createPane("kontur").style.zIndex = 450;
  peta.getPane("kontur").style.pointerEvents = "none";
  const kontur = LK.kontur({ pane: "kontur", attribution: atribusiDem }).addTo(peta);
  const hillshade = L.tileLayer("https://services.arcgisonline.com/arcgis/rest/services/Elevation/World_Hillshade/MapServer/tile/{z}/{y}/{x}",
    { opacity: 0.35, maxZoom: 16, attribution: "Relief: " + esri });
  let isiKlaster = 0.5;
  const byKey = Object.fromEntries(data.map(r => [norm(r.kecamatan), r]));
  const klaster = L.geoJSON(geo, {
    style: f => {
      const r = byKey[norm(f.properties.kecamatan)];
      return { fillColor: r ? WARNA[r.cluster_id] : "#CDBFBC", fillOpacity: isiKlaster, color: "#FFFCFB", weight: 1.5 };
    },
    onEachFeature: (f, l) => {
      const r = byKey[norm(f.properties.kecamatan)];
      if (r) {
        l.bindTooltip(`<b>${esc(r.kecamatan)}</b><br>Skor ${r.skor_topsis.toFixed(3)} · ${esc(r.cluster_name)}`);
        l.on("click", () => bukaDetail(r.slug));         // klik poligon = buka panel detail
        l.on("mouseover", () => l.setStyle({ weight: 3, color: "#2A1A19" }).bringToFront());
        l.on("mouseout", () => klaster.resetStyle(l));
      }
    },
  }).addTo(peta);

  L.control.layers(dasar, { "Garis kontur": kontur, "Bayangan relief": hillshade, "Klaster prioritas": klaster }, { collapsed: window.innerWidth < 700 }).addTo(peta);

  const legendaTopo = L.control({ position: "bottomright" });
  legendaTopo.onAdd = () => {
    const d = L.DomUtil.create("div", "legenda-topo");
    d.innerHTML = '<b>Membaca ketinggian</b>'
      + '<div class="kontur"><svg width="28" height="10" aria-hidden="true"><path d="M1 7 Q8 1 14 5 T27 3" fill="none" stroke="#46281A" stroke-width="1.5"/></svg>'
      + '<span>Kontur tiap 10 m (5 m saat diperbesar). Garis rapat = tanah cepat naik.</span></div>'
      + '<div class="kelas">' + LK.KELAS.map(k => `<span><i style="background:rgb(${k.warna})"></i>${k.label}</span>`).join("") + '</div>'
      + '<div class="teks"><span>Utara: dataran rendah</span><span>Selatan: lebih tinggi</span></div>';
    return d;
  };
  legendaTopo.addTo(peta);
  const kelasEl = () => legendaTopo.getContainer().querySelector(".kelas");
  kelasEl().style.display = "none";
  // di peta "Ketinggian" warna klaster dibuat lebih transparan supaya warna tinggi tanah terbaca
  peta.on("baselayerchange", e => {
    const tinggi = e.name.startsWith("Ketinggian");
    kelasEl().style.display = tinggi ? "" : "none";
    isiKlaster = tinggi ? 0.28 : 0.5;
    klaster.eachLayer(l => klaster.resetStyle(l));
  });
  const sinkronLegenda = () => { legendaTopo.getContainer().style.display = peta.hasLayer(kontur) || peta.hasLayer(dasar["Ketinggian (tinggi/rendah)"]) ? "" : "none"; };
  peta.on("overlayadd overlayremove baselayerchange", sinkronLegenda);

  const nama = {};
  data.forEach(r => nama[r.cluster_id] = r.cluster_name);
  document.getElementById("legend").innerHTML = Object.keys(nama).sort()
    .map(i => `<span><i style="background:${WARNA[i]}"></i>${esc(nama[i])}</span>`).join("");
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

// ── grafik mini di kartu KPI (SVG sederhana, warna mengikuti tema) ──
const G = window.KPI_GRAFIK || {};
const svg = (w, h, isi) => `<svg viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" aria-hidden="true">${isi}</svg>`;
const lebar = el => Math.max(160, Math.floor(el.clientWidth || 240));
const teks = (x, y, t, anchor = "middle") => `<text x="${x}" y="${y}" text-anchor="${anchor}" class="mini-teks">${esc(t)}</text>`;

// kolom dengan ujung atas membulat 4px, menempel ke garis dasar
function kolom(x, y, w, h, isi, judul) {
  const r = Math.min(4, w / 2, h);
  return `<path d="M${x},${y + h}V${y + r}q0,-${r} ${r},-${r}h${w - 2 * r}q${r},0 ${r},${r}V${y + h}Z" style="fill:${isi}"><title>${esc(judul)}</title></path>`;
}

function grafikKota() {
  const el = document.getElementById("mini-kota"); if (!el || !G.per_kota) return;
  const W = lebar(el), H = 64, n = G.per_kota.length, gap = 10, bw = (W - gap * (n - 1)) / n;
  const maks = Math.max(...G.per_kota.map(d => d[1])), tinggi = H - 30;
  el.innerHTML = svg(W, H, G.per_kota.map(([kota, v], i) => {
    const h = v / maks * tinggi, x = i * (bw + gap), y = 12 + tinggi - h;
    return kolom(x, y, bw, h, "var(--color-accent-fill)", `Jakarta ${kota}: ${v} kecamatan`)
      + teks(x + bw / 2, y - 3, v) + teks(x + bw / 2, H - 2, kota);
  }).join(""));
}

function grafikTahun() {
  const el = document.getElementById("mini-tahun"); if (!el) return;
  if (!G.per_tahun) { el.remove(); return; }
  const W = lebar(el), H = 64, n = G.per_tahun.length, gap = 4, bw = (W - gap * (n - 1)) / n;
  const maks = Math.max(...G.per_tahun.map(d => d[1])), tinggi = H - 18, dasar = 4 + tinggi;
  const yRata = dasar - G.rata / maks * tinggi;
  el.innerHTML = svg(W, H, G.per_tahun.map(([t, v], i) => {
    const h = v / maks * tinggi, x = i * (bw + gap);
    const label = (i === 0 || i === n - 1) ? teks(x + bw / 2, H - 2, t) : "";
    return kolom(x, dasar - h, bw, h, "var(--color-accent-fill)", `${t}: ${v.toFixed(1)} kejadian per kecamatan`) + label;
  }).join("") + `<line x1="0" x2="${W}" y1="${yRata}" y2="${yRata}" class="mini-rata"><title>Rata-rata ${G.rata.toFixed(1)}</title></line>`);
}

function grafikKlaster() {
  const el = document.getElementById("mini-klaster"); if (!el) return;
  const nama = {}, jml = [0, 0, 0, 0];
  data.forEach(r => { jml[r.cluster_id]++; nama[r.cluster_id] = r.cluster_name; });
  const W = lebar(el), gap = 2; let x = 0;
  const lebarTersedia = W - gap * (jml.filter(v => v).length - 1);
  const batang = jml.map((v, i) => {
    if (!v) return "";
    const w = v / data.length * lebarTersedia, seg = `<rect x="${x}" y="0" width="${w}" height="12" rx="3" style="fill:${WARNA[i]}"><title>${esc(nama[i])}: ${v} kecamatan</title></rect>`;
    x += w + gap; return seg;
  }).join("");
  el.innerHTML = svg(W, 12, batang) + `<div class="mini-legenda">${jml.map((v, i) => v ? `<span><i style="background:${WARNA[i]}"></i>${esc(nama[i])} ${v}</span>` : "").join("")}</div>`;
}

function grafikSkor() {
  const el = document.getElementById("mini-skor"); if (!el) return;
  // histogram skor 0–1 (lebar kelompok 0,05), tiap kolom ditumpuk menurut klaster
  const W = lebar(el), H = 64, nKel = 20, gap = 2, bw = (W - gap * (nKel - 1)) / nKel, tinggi = H - 18, dasar = 4 + tinggi;
  const kel = Array.from({ length: nKel }, () => [0, 0, 0, 0]);
  data.forEach(r => kel[Math.min(nKel - 1, Math.floor(r.skor_topsis * nKel))][r.cluster_id]++);
  const maks = Math.max(...kel.map(k => k.reduce((a, b) => a + b, 0)));
  const nama = {}; data.forEach(r => { nama[r.cluster_id] = r.cluster_name; });
  let isi = `<line x1="0" x2="${W}" y1="${dasar + 0.5}" y2="${dasar + 0.5}" class="mini-sumbu"/>`;
  kel.forEach((k, i) => {
    const x0 = i * (bw + gap), total = k.reduce((a, b) => a + b, 0); if (!total) return;
    let y = dasar;
    const rentang = `${(i / nKel).toFixed(2)}–${((i + 1) / nKel).toFixed(2)}`;
    [3, 2, 1, 0].forEach(c => {
      if (!k[c]) return;
      const h = k[c] / maks * tinggi; y -= h;
      const atas = ![0, 1, 2, 3].some(d => d < c && k[d]);     // segmen teratas dapat ujung membulat
      const judul = `Skor ${rentang}: ${k[c]} kecamatan ${nama[c]} (total ${total})`;
      isi += atas ? kolom(x0, y, bw, h, WARNA[c], judul)
                  : `<rect x="${x0}" y="${y}" width="${bw}" height="${h}" style="fill:${WARNA[c]}"><title>${esc(judul)}</title></rect>`;
    });
  });
  isi += [0, 0.5, 1].map(v => teks(v * W, H - 2, v === 0.5 ? "0,5" : v, v === 0 ? "start" : v === 1 ? "end" : "middle")).join("");
  el.innerHTML = svg(W, H, isi);
}

let tundaUkuran;
addEventListener("resize", () => {
  clearTimeout(tundaUkuran);
  tundaUkuran = setTimeout(() => { if (data.length) { grafikKota(); grafikTahun(); grafikKlaster(); grafikSkor(); } }, 150);
});

// KPI dan tiga teratas mengikuti bobot aktif (saat bobot bawaan, isinya sama dengan yang dirender server)
function perbaruiRingkasan() {
  const urut3 = [...data].sort((a, b) => a.rank_topsis - b.rank_topsis);
  const nTinggi = data.filter(r => r.cluster_id === 0).length;
  document.getElementById("kpi-prioritas").textContent = nTinggi;
  grafikKlaster(); grafikSkor();
  const skor = data.map(r => r.skor_topsis);
  document.getElementById("kpi-skor").textContent = `${Math.min(...skor).toFixed(2)} – ${Math.max(...skor).toFixed(2)}`;
  const judul = s => String(s).toLowerCase().replace(/(^|\s)\S/g, c => c.toUpperCase());
  document.getElementById("top3").innerHTML = urut3.slice(0, 3).map(r => `
    <div class="rank-row" data-slug="${esc(r.slug)}" tabindex="0">
      <span class="no">#${r.rank_topsis}</span>
      <span class="name"><b>${esc(judul(r.kecamatan))}</b> · ${esc(judul(r.wilayah))}<br>
        ${r.kejadian_per_tahun.toFixed(1)} kali banjir/tahun · air maks ${Math.trunc(r.tinggi_max_cm)} cm · skor ${r.skor_topsis.toFixed(3)}
        <span class="bar" aria-hidden="true"><i class="fill-c${r.cluster_id}" style="width:${Math.round(r.skor_topsis * 100)}%"></i></span></span>
      <span class="pill c${r.cluster_id}">${esc(r.cluster_name)}</span>
    </div>`).join("");
}

// grafik KPI dan tabel tidak menunggu peta: peta (Leaflet + tile luar) bisa lambat atau gagal sendiri
grafikKota(); grafikTahun();
const muat = window.BobotAktif.muatData().then(hasil => {
  data = hasil.kecamatan; mulaiTabel(); perbaruiRingkasan();
  const awal = new URLSearchParams(location.search).get("detail");     // tautan langsung: /?detail=kebon-jeruk
  if (awal) bukaDetail(awal);
});
Promise.all([muat, fetch("/api/geojson").then(r => r.json())])
  .then(([, geo]) => buatPeta(geo))
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
  dlg.style.setProperty("--tier", WARNA[r.cluster_id]);
  document.getElementById("detail-isi").innerHTML = `
    <h2>${esc(r.kecamatan)}</h2>
    <div class="muted">${esc(r.wilayah)}</div>
    <div class="detail-ringkas">
      <div><span class="muted">Peringkat</span><b>#${r.rank_topsis} dari ${data.length}</b></div>
      <div><span class="muted">Skor risiko</span><b>${r.skor_topsis.toFixed(3)}</b></div>
      <div><span class="muted">Klaster</span><b><span class="pill c${r.cluster_id}">${esc(r.cluster_name)}</span></b></div>
    </div>
    ${r.silhouette_sample < 0.1 ? '<div class="muted"><span class="batas">▲</span> Kecamatan batas: posisi klasternya kurang pasti</div>' : ""}
    <h3>Nilai tiap kriteria</h3>
    <div class="tabel-wrap"><table class="table"><tbody>${window.KRITERIA.map(k =>
      `<tr><td>${esc(k.desc)}</td><td class="muted">${esc(k.satuan)}</td><td class="num">${nilaiId(r[k.kolom])}</td></tr>`).join("")}</tbody></table></div>
    <h3>Tindakan yang disarankan</h3>
    ${tindakan ? `<ul>${tindakan.map(t => `<li>${esc(t.tindakan)}</li>`).join("")}</ul>`
               : '<div class="placeholder">Rekomendasi belum ditetapkan.</div>'}
    <div class="muted" style="margin-top:6px">${esc(window.CATATAN)}<br>Sumber: ${esc(window.SUMBER_REK)}</div>
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
