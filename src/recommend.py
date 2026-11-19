"""Rekomendasi tindakan awal per klaster.

Kerangka: Perka BNPB No. 2 Tahun 2012 (Pedoman Umum Pengkajian Risiko Bencana), yaitu
Risiko = Bahaya x Kerentanan / Kapasitas. Dokumen itu mengatur cara menilai risiko, bukan daftar
tindakan per klaster; jadi isi tindakan di bawah adalah DRAF AWAL yang disusun mengikuti dimensi
Bahaya, Kerentanan, dan Kapasitas, dan wajib divalidasi tim lapangan/BPBD sebelum dipakai.
"""

SUMBER = "Kerangka Perka BNPB 02/2012 (draf awal, belum divalidasi lapangan)"
CATATAN_VALIDASI = "Ini rekomendasi awal dan perlu dicek oleh tim lapangan. Keputusan akhir ada pada BPBD."


def _t(tindakan, prioritas):
    return {"tindakan": tindakan, "prioritas": prioritas, "sumber": SUMBER}


RULES = {
    0: [  # Prioritas Tinggi
        _t("Pasang alat peringatan dini (EWS) di kecamatan yang belum punya. Uji alatnya sebelum setiap musim hujan.", "tinggi"),
        _t("Adakan sosialisasi kesiapsiagaan banjir di tingkat kelurahan, minimal 2 kali setahun.", "tinggi"),
        _t("Tentukan jalur dan titik evakuasi, lalu beri tanda yang jelas. Latih warga lewat simulasi evakuasi setiap tahun.", "tinggi"),
        _t("Perbaiki saluran air kecil dan bersihkan saluran di titik yang sering tergenang.", "tinggi"),
        _t("Siapkan pompa, perahu karet, dan posko sebelum musim hujan di kelurahan yang genangannya paling lama.", "sedang"),
        _t("Utamakan lansia, anak-anak, dan penyandang disabilitas dalam rencana evakuasi kelurahan.", "sedang"),
    ],
    1: [  # Waspada
        _t("Lengkapi alat peringatan dini (EWS) di kelurahan rawan yang belum terpantau.", "tinggi"),
        _t("Periksa dan bersihkan saluran air serta pintu air sebelum musim hujan.", "sedang"),
        _t("Sosialisasikan kesiapsiagaan banjir dan rencana evakuasi di tingkat RT/RW, minimal 1 kali setahun.", "sedang"),
        _t("Tentukan titik kumpul dan umumkan nomor kontak darurat kelurahan.", "sedang"),
        _t("Pantau genangan setiap musim hujan. Jika kejadian bertambah, naikkan ke penanganan prioritas.", "sedang"),
    ],
    2: [  # Menengah
        _t("Pantau kondisi saluran dan titik genangan setiap bulan selama musim hujan.", "sedang"),
        _t("Rawat alat peringatan dini yang sudah ada dan latih relawan kelurahan.", "sedang"),
        _t("Sosialisasikan kesiapsiagaan banjir lewat RT/RW setiap tahun.", "rendah"),
        _t("Perbarui rencana darurat kelurahan secara berkala.", "rendah"),
    ],
    3: [  # Rendah
        _t("Jaga sistem peringatan dini tetap berfungsi dan rawat saluran air secara rutin.", "rendah"),
        _t("Cek catatan banjir di lapangan sebelum menurunkan prioritas suatu kecamatan.", "sedang"),
        _t("Pantau kejadian banjir dari tahun ke tahun. Hitung ulang klaster saat ada data baru.", "rendah"),
        _t("Pastikan warga tahu jalur evakuasi dan nomor kontak darurat.", "rendah"),
    ],
}


def rekomendasi(cluster_id):
    """Daftar tindakan (dict: tindakan, prioritas, sumber) untuk klaster, atau None jika belum ada."""
    return RULES.get(int(cluster_id)) or None
