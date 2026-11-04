# Deploy ke PythonAnywhere (akun gratis)

Ganti `<user>` dengan nama akun PythonAnywhere Anda. Semua perintah dijalankan di **Bash console** PythonAnywhere.

## 1. Pasang

```bash
git clone https://github.com/Aceranzer/Geopulse-id.git
cd Geopulse-id
mkvirtualenv --python=/usr/bin/python3.12 geopulse     # pilih versi Python yang tersedia di akun Anda
pip install -r requirements-web.txt                    # bukan requirements.txt: geopandas tidak diperlukan website
```

Cek apakah PDF server bisa dipakai (WeasyPrint butuh pustaka sistem Pango/Cairo):

```bash
python -c "import weasyprint; print('WeasyPrint OK')"
python -m pytest tests -q
```

Jika `import weasyprint` gagal, website tetap jalan: tombol PDF otomatis memakai halaman cetak
(dialog cetak browser, pilih "Simpan sebagai PDF"). Tes `test_weasyprint_asli` akan dilewati.

## 2. Buat web app

Tab **Web** → *Add a new web app* → **Manual configuration** → pilih versi Python yang sama.

| Pengaturan | Isi |
|---|---|
| Source code | `/home/<user>/Geopulse-id` |
| Virtualenv | `/home/<user>/.virtualenvs/geopulse` |
| Static files | URL `/static/` → `/home/<user>/Geopulse-id/static` |

## 3. File WSGI

Buka file WSGI yang ditautkan di tab Web, hapus isinya, lalu isi:

```python
import os
import sys

path = "/home/<user>/Geopulse-id"
if path not in sys.path:
    sys.path.insert(0, path)

# Rahasia diisi di sini (file ini ada di server, bukan di repo). Jangan pernah commit nilai asli.
os.environ["SECRET_KEY"] = "ganti-dengan-teks-acak-panjang"

from app import app as application
```

Buat teks acak untuk `SECRET_KEY`: `python -c "import secrets; print(secrets.token_hex(32))"`.
Debug Flask tetap mati (`app.run(debug=False)`; di PythonAnywhere aplikasi dijalankan lewat WSGI).

Tekan tombol **Reload** di tab Web, lalu buka `https://<user>.pythonanywhere.com`.

## 4. Periksa

- Halaman `/`, `/simulasi`, `/komparasi`, `/klaster`, `/metodologi` terbuka dan peta muncul.
- Klik satu baris tabel → panel detail terbuka → "Unduh profil (PDF)" menghasilkan PDF atau membuka dialog cetak.
- Jika ada galat: tab Web → *Error log*.

Catatan akun gratis: server tidak bisa mengakses internet bebas (hanya situs dalam daftar putih).
Itu tidak memengaruhi website ini karena peta dan font dimuat oleh browser pengunjung, bukan server.

## 5. Update berikutnya

```bash
cd ~/Geopulse-id
git pull
```

Lalu tekan **Reload** di tab Web (atau `touch /var/www/<user>_pythonanywhere_com_wsgi.py`).
