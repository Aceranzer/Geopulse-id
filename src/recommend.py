"""Aturan rekomendasi tindakan per klaster.

Isi aturan harus ditetapkan tim (acuan pedoman BNPB atau pedoman daerah), bukan dikarang di sini.
Selama RULES kosong, website menampilkan placeholder "Rekomendasi belum ditetapkan".
Format yang diharapkan: RULES = {0: ["tindakan 1", "tindakan 2"], 1: [...], 2: [...], 3: [...]}
"""

RULES = {}


def rekomendasi(cluster_id):
    """Daftar tindakan untuk klaster, atau None jika belum ditetapkan."""
    return RULES.get(int(cluster_id)) or None
