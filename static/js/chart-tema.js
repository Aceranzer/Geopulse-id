// Tema Chart.js bersama: font, warna, tooltip. Dimuat setelah Chart.js, sebelum skrip halaman.
(function () {
  const INK = "#2A1A19", MUTED = "#6A5552", GRID = "#EDE3E1";
  const D = Chart.defaults;
  D.font.family = '"Inter", system-ui, sans-serif';
  D.font.size = 13;
  D.color = MUTED;
  D.borderColor = GRID;
  D.plugins.legend.labels.usePointStyle = true;
  D.plugins.legend.labels.boxWidth = 10;
  D.plugins.legend.labels.boxHeight = 10;
  D.plugins.legend.labels.padding = 16;
  Object.assign(D.plugins.tooltip, {
    backgroundColor: INK, titleColor: "#F2D479", bodyColor: "#F1E8E6",
    titleFont: { family: '"Plus Jakarta Sans", "Inter", sans-serif', weight: "700", size: 13 },
    bodyFont: { family: '"JetBrains Mono", monospace', size: 12 },
    padding: 12, cornerRadius: 12, boxPadding: 4, displayColors: true,
  });
  D.elements.bar.borderRadius = 8;
  D.elements.bar.borderSkipped = false;
  D.elements.line.borderWidth = 3;

  // Teks kanvas tidak digambar ulang setelah font web selesai dimuat, jadi grafik dibuat setelah font siap.
  window.TemaGrafik = {
    // paling lama 1,5 detik: jangan menahan halaman bila server font lambat
    siap: Promise.race([
      (document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()).catch(() => {}),
      new Promise(r => setTimeout(r, 1500)),
    ]),
    skala: {
      grid: { color: GRID, drawTicks: false },
      border: { display: false },
      ticks: { padding: 8 },
      title: { color: MUTED, font: { weight: "600" } },
    },
  };
})();
