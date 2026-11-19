// Lapisan ketinggian dan garis kontur, dihitung di browser dari ubin elevasi publik
// (AWS Terrain Tiles, format "terrarium": tinggi = R*256 + G + B/256 - 32768 meter; sumber utama SRTM).
// Tidak menambah data ke proyek: ubin dibaca langsung seperti ubin peta biasa.
(function () {
  const URL_UBIN = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png";

  // kelas ketinggian (meter) dan warnanya: satu rona, terang = rendah, gelap = tinggi
  const KELAS = [
    { batas: 2,  warna: [240, 246, 236], label: "< 2 m" },
    { batas: 5,  warna: [214, 232, 200], label: "2–5 m" },
    { batas: 10, warna: [236, 226, 178], label: "5–10 m" },
    { batas: 25, warna: [222, 196, 138], label: "10–25 m" },
    { batas: 50, warna: [196, 152, 98],  label: "25–50 m" },
    { batas: Infinity, warna: [150, 104, 62], label: "> 50 m" },
  ];
  const kelasDari = t => { for (let i = 0; i < KELAS.length; i++) if (t < KELAS[i].batas) return i; return KELAS.length - 1; };

  const cache = new Map();
  function muatTinggi(z, x, y) {
    const kunci = `${z}/${x}/${y}`;
    if (cache.has(kunci)) return cache.get(kunci);
    const janji = new Promise((ok, gagal) => {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => {
        const c = document.createElement("canvas"); c.width = c.height = 256;
        const g = c.getContext("2d"); g.drawImage(img, 0, 0);
        const p = g.getImageData(0, 0, 256, 256).data, t = new Float32Array(256 * 256);
        for (let i = 0; i < t.length; i++) t[i] = p[i * 4] * 256 + p[i * 4 + 1] + p[i * 4 + 2] / 256 - 32768;
        ok(haluskan(t));
      };
      img.onerror = gagal;
      img.src = URL_UBIN.replace("{z}", z).replace("{x}", x).replace("{y}", y);
    });
    cache.set(kunci, janji);
    return janji;
  }

  // rata-rata 7x7: meredam derau gedung/pepohonan pada data radar supaya kontur tidak bergerigi
  function haluskan(t) {
    const n = 256, r = 3, hasil = new Float32Array(n * n);
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
      let s = 0, k = 0;
      for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
        const xx = x + dx, yy = y + dy;
        if (xx >= 0 && yy >= 0 && xx < n && yy < n) { s += t[yy * n + xx]; k++; }
      }
      hasil[y * n + x] = s / k;
    }
    return hasil;
  }

  // mode "warna": isi tiap piksel dengan warna kelasnya; mode "kontur": garis tiap `jarak` meter
  const Lapisan = L.GridLayer.extend({
    options: { mode: "warna", maxNativeZoom: 14, minNativeZoom: 9, tileSize: 256 },
    createTile(coords, selesai) {
      const kanvas = document.createElement("canvas"); kanvas.width = kanvas.height = 256;
      muatTinggi(coords.z, coords.x, coords.y).then(t => {
        const g = kanvas.getContext("2d"), img = g.createImageData(256, 256), d = img.data;
        if (this.options.mode === "warna") {
          for (let i = 0; i < t.length; i++) {
            const w = t[i] <= 0 ? [205, 225, 240] : KELAS[kelasDari(t[i])].warna;   // laut / di bawah 0 m
            d[i * 4] = w[0]; d[i * 4 + 1] = w[1]; d[i * 4 + 2] = w[2]; d[i * 4 + 3] = 255;
          }
        } else {
          // jarak kontur menyesuaikan zoom: 10 m saat jauh, 5 m saat diperbesar; garis tebal tiap 5 jarak
          const jarak = coords.z >= 13 ? 5 : 10, indeks = jarak * 5, pita = v => Math.floor(Math.max(v, 0) / jarak);
          for (let y = 0; y < 255; y++) for (let x = 0; x < 255; x++) {
            const i = y * 256 + x, a = pita(t[i]), b = Math.max(pita(t[i + 1]), pita(t[i + 256]));
            if (a !== b && Math.max(t[i], t[i + 1], t[i + 256]) > 0.5) {
              const tebal = (Math.max(a, b) * jarak) % indeks === 0;
              d[i * 4] = 70; d[i * 4 + 1] = 40; d[i * 4 + 2] = 20; d[i * 4 + 3] = tebal ? 255 : 170;
              if (tebal && x < 254) { const j = i + 1; d[j * 4] = 70; d[j * 4 + 1] = 40; d[j * 4 + 2] = 20; d[j * 4 + 3] = 255; }
            }
          }
        }
        g.putImageData(img, 0, 0);
        selesai(null, kanvas);
      }).catch(e => selesai(e, kanvas));
      return kanvas;
    },
  });

  window.LapisanKetinggian = {
    warna: opsi => new Lapisan({ mode: "warna", ...opsi }),
    kontur: opsi => new Lapisan({ mode: "kontur", ...opsi }),
    KELAS,
  };
})();
