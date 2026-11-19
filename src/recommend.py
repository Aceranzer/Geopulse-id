"""Rekomendasi tindakan awal per klaster.

Kerangka: Perka BNPB No. 2 Tahun 2012 (Pedoman Umum Pengkajian Risiko Bencana), yaitu
Risiko = Bahaya x Kerentanan / Kapasitas. Dokumen itu mengatur cara menilai risiko, bukan daftar
tindakan per klaster; jadi isi tindakan di bawah adalah DRAF AWAL untuk petugas pemerintah yang disusun mengikuti dimensi
Bahaya, Kerentanan, dan Kapasitas, dan wajib divalidasi tim lapangan/BPBD sebelum dipakai.
"""

SUMBER = "Kerangka Perka BNPB 02/2012 (draf awal, belum divalidasi lapangan)"
CATATAN_VALIDASI = ("Rekomendasi ini ditujukan untuk petugas pemerintah dan masih berupa draf awal. "
                    "Pembagian tugas antar dinas perlu disesuaikan dengan aturan setempat dan dicek oleh tim lapangan. "
                    "Keputusan akhir ada pada BPBD.")


def _t(tindakan, prioritas):
    return {"tindakan": tindakan, "prioritas": prioritas, "sumber": SUMBER}


# Setiap tindakan ditulis sebagai tugas untuk petugas (BPBD, Dinas SDA, Dinas Sosial, camat, lurah).
RULES = {
    0: [  # Prioritas Tinggi
        _t("BPBD dan Dinas SDA memasang alat peringatan dini (EWS) di kelurahan yang belum punya. Uji alatnya sebelum setiap musim hujan.", "tinggi"),
        _t("Camat dan lurah mengadakan sosialisasi kesiapsiagaan banjir di tingkat kelurahan, minimal 2 kali setahun.", "tinggi"),
        _t("BPBD bersama kelurahan menentukan jalur dan titik evakuasi, lalu memasang tandanya. Adakan simulasi evakuasi bersama warga setiap tahun.", "tinggi"),
        _t("Dinas SDA memperbaiki saluran air kecil dan membersihkan saluran di titik yang sering tergenang.", "tinggi"),
        _t("BPBD menyiapkan pompa, perahu karet, dan posko sebelum musim hujan di kelurahan yang genangannya paling lama.", "sedang"),
        _t("Dinas Sosial dan kelurahan mendahulukan lansia, anak-anak, dan penyandang disabilitas dalam rencana evakuasi.", "sedang"),
    ],
    1: [  # Waspada
        _t("BPBD melengkapi alat peringatan dini (EWS) di kelurahan rawan yang belum terpantau.", "tinggi"),
        _t("Dinas SDA memeriksa dan membersihkan saluran air serta pintu air sebelum musim hujan.", "sedang"),
        _t("Lurah dan pengurus RT/RW mensosialisasikan kesiapsiagaan banjir dan rencana evakuasi, minimal 1 kali setahun.", "sedang"),
        _t("Kelurahan menentukan titik kumpul dan mengumumkan nomor kontak darurat.", "sedang"),
        _t("BPBD memantau genangan setiap musim hujan. Jika kejadian bertambah, naikkan ke penanganan prioritas.", "sedang"),
    ],
    2: [  # Menengah
        _t("Dinas SDA memantau kondisi saluran dan titik genangan setiap bulan selama musim hujan.", "sedang"),
        _t("BPBD merawat alat peringatan dini yang sudah ada dan melatih relawan kelurahan.", "sedang"),
        _t("Lurah dan pengurus RT/RW mensosialisasikan kesiapsiagaan banjir setiap tahun.", "rendah"),
        _t("Kelurahan memperbarui rencana darurat secara berkala.", "rendah"),
    ],
    3: [  # Rendah
        _t("BPBD menjaga sistem peringatan dini tetap berfungsi, dan Dinas SDA merawat saluran air secara rutin.", "rendah"),
        _t("Petugas kecamatan mengecek catatan banjir di lapangan sebelum menurunkan prioritas suatu kecamatan.", "sedang"),
        _t("BPBD memantau kejadian banjir dari tahun ke tahun dan menghitung ulang klaster saat ada data baru.", "rendah"),
        _t("Lurah memastikan warga tahu jalur evakuasi dan nomor kontak darurat.", "rendah"),
    ],
}


def rekomendasi(cluster_id):
    """Daftar tindakan (dict: tindakan, prioritas, sumber) untuk klaster, atau None jika belum ada."""
    return RULES.get(int(cluster_id)) or None
