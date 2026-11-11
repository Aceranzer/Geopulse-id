// Bobot aktif per sesi tab: disimpan di sessionStorage (hilang saat tab ditutup, tidak terbawa antar-sesi).
// Dipakai semua halaman: muatData() mengembalikan hasil sesuai bobot aktif (atau bobot bawaan bila tidak ada).
(function () {
  const KUNCI = "geopulse_bobot_aktif";
  const NAMA = { entropi: "Entropi (bawaan)", sama: "Sama rata", pakar: "Pakar", kustom: "Kustom" };

  function get() {
    try {
      const j = JSON.parse(sessionStorage.getItem(KUNCI));
      return j && NAMA[j.preset] && Array.isArray(j.bobot) && j.bobot.length === 8 ? j : null;
    } catch (e) { return null; }
  }

  function reset() {
    try { sessionStorage.removeItem(KUNCI); } catch (e) { /* penyimpanan diblokir: abaikan */ }
  }

  // bobot entropi = bawaan, jadi menerapkannya sama dengan mereset
  function set(preset, bobot) {
    if (preset === "entropi") { reset(); return; }
    try { sessionStorage.setItem(KUNCI, JSON.stringify({ preset, bobot })); } catch (e) { /* abaikan */ }
  }

  const headers = { "Content-Type": "application/json" };

  // {aktif, preset, bobot, kecamatan, klaster, sweep, k_final, metrics}
  async function muatData() {
    const a = get();
    if (a) {
      try {
        const r = await fetch("/api/pipeline", { method: "POST", headers, body: JSON.stringify({ preset: a.preset, bobot: a.bobot }) });
        if (r.ok) return { ...(await r.json()), aktif: true, preset: a.preset };
      } catch (e) { /* jatuh ke bobot bawaan */ }
      reset();                                    // bobot tersimpan tidak valid / server menolak
    }
    const [kecamatan, klaster, sw] = await Promise.all(
      ["/api/kecamatan", "/api/klaster", "/api/sweep"].map(u => fetch(u).then(r => r.json())));
    return { aktif: false, preset: "entropi", bobot: null, kecamatan, klaster, sweep: sw.sweep, k_final: sw.k_final, metrics: null };
  }

  // potongan query untuk tautan PDF profil kecamatan: "?w=..&p=.." atau "" bila bobot bawaan
  function queryPdf() {
    const a = get();
    return a ? "?w=" + a.bobot.join(",") + "&p=" + encodeURIComponent(a.preset) : "";
  }

  function pasangBanner() {
    const el = document.getElementById("banner-bobot");
    if (!el) return;
    const a = get();
    el.hidden = !a;
    if (!a) return;
    document.getElementById("banner-nama").textContent = NAMA[a.preset];
    if (el.dataset.siap) return;                  // pasang pendengar sekali saja
    el.dataset.siap = "1";
    const ke = () => { location.href = "/simulasi"; };
    el.addEventListener("click", ke);
    el.addEventListener("keydown", e => { if (e.key === "Enter") ke(); });
    document.getElementById("banner-reset").addEventListener("click", e => {
      e.stopPropagation();                        // jangan ikut membuka halaman Simulasi
      reset();
      location.reload();
    });
  }

  window.BobotAktif = { NAMA, get, set, reset, muatData, queryPdf, pasangBanner };
  document.addEventListener("DOMContentLoaded", pasangBanner);
})();
