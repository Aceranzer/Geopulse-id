"""Rekomendasi tindakan awal per klaster.

Kerangka: Perka BNPB No. 2 Tahun 2012 (Pedoman Umum Pengkajian Risiko Bencana), yaitu
Risiko = Bahaya x Kerentanan / Kapasitas. Dokumen itu mengatur cara menilai risiko, bukan daftar
tindakan per klaster; jadi isi tindakan di bawah adalah DRAF AWAL yang disusun mengikuti dimensi
Bahaya, Kerentanan, dan Kapasitas, dan wajib divalidasi tim lapangan/BPBD sebelum dipakai.
"""

SUMBER = "Kerangka Perka BNPB 02/2012 (draf awal, belum divalidasi lapangan)"
CATATAN_VALIDASI = "Rekomendasi awal; perlu divalidasi tim lapangan. Keputusan final ada pada BPBD."


def _t(tindakan, prioritas):
    return {"tindakan": tindakan, "prioritas": prioritas, "sumber": SUMBER}


RULES = {
    0: [  # Prioritas Tinggi
        _t("Tambah alat peringatan dini (EWS) dan uji fungsinya secara berkala", "tinggi"),
        _t("Perbaiki drainase mikro dan normalisasi saluran di titik genangan berulang", "tinggi"),
        _t("Siapkan jalur dan titik evakuasi, lakukan sosialisasi dan simulasi evakuasi rutin ke warga", "tinggi"),
        _t("Siagakan pompa dan perahu karet menjelang musim hujan", "sedang"),
    ],
    1: [  # Waspada
        _t("Lengkapi alat peringatan dini (EWS) di kelurahan yang belum terpantau", "tinggi"),
        _t("Periksa dan bersihkan saluran air sebelum musim hujan", "sedang"),
        _t("Sosialisasi kesiapsiagaan banjir dan rencana evakuasi tingkat RT/RW", "sedang"),
    ],
    2: [  # Menengah
        _t("Pantau kondisi saluran dan titik genangan secara berkala", "sedang"),
        _t("Pertahankan alat peringatan dini dan latih relawan kelurahan", "sedang"),
        _t("Lakukan sosialisasi kesiapsiagaan secara berkala", "rendah"),
    ],
    3: [  # Rendah
        _t("Pertahankan sistem peringatan dini dan pemeliharaan saluran yang ada", "rendah"),
        _t("Pantau perubahan kejadian banjir dari tahun ke tahun", "rendah"),
        _t("Pastikan warga mengetahui jalur evakuasi dan kontak darurat", "rendah"),
    ],
}


def rekomendasi(cluster_id):
    """Daftar tindakan (dict: tindakan, prioritas, sumber) untuk klaster, atau None jika belum ada."""
    return RULES.get(int(cluster_id)) or None
