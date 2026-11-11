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
        _t("Prioritaskan pemasangan alat peringatan dini (EWS) tambahan di kecamatan yang belum memilikinya; uji fungsinya sebelum setiap musim hujan", "tinggi"),
        _t("Lakukan sosialisasi kesiapsiagaan musim hujan di tingkat kelurahan minimal 2 kali per tahun", "tinggi"),
        _t("Tetapkan dan tandai jalur serta titik evakuasi; adakan simulasi evakuasi bersama warga setiap tahun", "tinggi"),
        _t("Perbaiki drainase mikro dan normalisasi saluran di titik genangan yang berulang", "tinggi"),
        _t("Siagakan pompa, perahu karet, dan posko di kelurahan dengan genangan terlama sebelum musim hujan", "sedang"),
        _t("Dahulukan kelompok rentan (lansia, anak, penyandang disabilitas) dalam rencana evakuasi kelurahan", "sedang"),
    ],
    1: [  # Waspada
        _t("Lengkapi alat peringatan dini (EWS) di kelurahan rawan yang belum terpantau", "tinggi"),
        _t("Periksa dan bersihkan saluran air serta pintu air sebelum musim hujan", "sedang"),
        _t("Sosialisasikan kesiapsiagaan banjir dan rencana evakuasi tingkat RT/RW minimal 1 kali per tahun", "sedang"),
        _t("Tetapkan dan umumkan titik kumpul serta nomor kontak darurat kelurahan", "sedang"),
        _t("Pantau tren genangan tiap musim hujan; naikkan ke penanganan prioritas bila kejadian meningkat", "sedang"),
    ],
    2: [  # Menengah
        _t("Pantau kondisi saluran dan titik genangan setiap bulan selama musim hujan", "sedang"),
        _t("Pertahankan alat peringatan dini yang ada dan latih relawan kelurahan", "sedang"),
        _t("Sosialisasikan kesiapsiagaan melalui RT/RW setiap tahun", "rendah"),
        _t("Perbarui rencana kontinjensi kelurahan secara berkala", "rendah"),
    ],
    3: [  # Rendah
        _t("Pertahankan sistem peringatan dini dan pemeliharaan rutin saluran yang sudah ada", "rendah"),
        _t("Cocokkan hasil dengan catatan banjir lapangan sebelum menurunkan prioritas suatu kecamatan", "sedang"),
        _t("Pantau perubahan kejadian banjir dari tahun ke tahun dan hitung ulang klaster saat data baru masuk", "rendah"),
        _t("Pastikan warga mengetahui jalur evakuasi dan kontak darurat", "rendah"),
    ],
}


def rekomendasi(cluster_id):
    """Daftar tindakan (dict: tindakan, prioritas, sumber) untuk klaster, atau None jika belum ada."""
    return RULES.get(int(cluster_id)) or None
