# RPA SAP VL02N — Otomatisasi Penghapusan LO

Aplikasi SAP Automasi VL02N PT Pertamina Patra Niaga.  
Mengotomatisasi proses penghapusan (flag for deletion) Loading Order (LO) secara batch melalui transaksi SAP **VL02N** menggunakan SAP GUI Scripting.

---

## Fitur

- Membaca daftar nomor LO dari file **Excel (.xlsx)** atau **CSV**.
- Login ke SAP otomatis atau menggunakan sesi SAP yang sudah aktif.
- Menandai setiap LO untuk dihapus (*Flag for Deletion*) di transaksi VL02N.
- Menyimpan hasil proses (berhasil/gagal/tidak ditemukan) ke file Excel.
- Mencatat log detail ke file dan konsol.
- Mendukung **mode simulasi (dry-run)** untuk pengujian tanpa mengubah data SAP.
- Percobaan ulang otomatis (*retry*) jika terjadi error.

---

## Prasyarat

| Kebutuhan | Versi |
|-----------|-------|
| Python | 3.8 atau lebih baru |
| SAP GUI | 7.40 atau lebih baru (dengan SAP GUI Scripting diaktifkan) |
| Sistem Operasi | Windows |

### Mengaktifkan SAP GUI Scripting

1. Buka SAP GUI → **Options** → **Accessibility & Scripting** → **Scripting**.
2. Centang **Enable Scripting**.
3. Hubungi administrator SAP untuk mengaktifkan parameter `sapgui/user_scripting = TRUE` di sisi server.

---

## Instalasi

```bash
# Clone repositori
git clone https://github.com/arisman-piliang7/RPA-Robotic-Process-Automation-SAP-vl02n-.git
cd RPA-Robotic-Process-Automation-SAP-vl02n-

# Buat virtual environment (opsional tapi disarankan)
python -m venv venv
venv\Scripts\activate   # Windows

# Install dependensi
pip install -r requirements.txt
```

---

## Konfigurasi

Salin dan sesuaikan file `config.ini`:

```ini
[SAP]
system_name = PRD          ; Nama sistem di SAP Logon Pad
client      = 300          ; Nomor client SAP
username    = USERNAME     ; Username SAP (atau set env var SAP_USERNAME)
language    = ID           ; Bahasa (ID = Indonesia)
; password tidak dicantumkan di sini — wajib menggunakan env var SAP_PASSWORD

[FILE]
input_file    = data/daftar_lo.xlsx   ; File daftar LO (xlsx atau csv)
sheet_name    = Sheet1                ; Sheet Excel (kosongkan jika CSV)
kolom_nomor_lo = NOMOR_LO            ; Nama kolom berisi nomor LO
output_file   = output/hasil_hapus_lo.xlsx

[SETTINGS]
delay    = 1       ; Jeda antar langkah (detik)
max_retry = 3      ; Percobaan ulang jika gagal
dry_run  = False   ; True = mode simulasi
```

> **Keamanan:** Hindari menyimpan password di `config.ini`.  
> Gunakan environment variable `SAP_USERNAME` dan `SAP_PASSWORD`:
> ```bash
> set SAP_USERNAME=namauser
> set SAP_PASSWORD=katasandi
> ```

---

## Format File Input

Siapkan file Excel atau CSV dengan kolom `NOMOR_LO` (nama kolom sesuai konfigurasi):

| NOMOR_LO   |
|------------|
| 0080012345 |
| 0080012346 |
| 0080012347 |

Contoh file tersedia di: `data/daftar_lo_contoh.csv`

---

## Penggunaan

```bash
# Jalankan dengan konfigurasi default
python main.py

# Tentukan file konfigurasi secara eksplisit
python main.py --config config.ini

# Mode simulasi (tidak ada perubahan di SAP)
python main.py --dry-run

# Mode simulasi dengan log detail
python main.py --dry-run --log-level DEBUG
```

### Argumen Baris Perintah

| Argumen | Keterangan | Default |
|---------|-----------|---------|
| `--config` | Path ke file konfigurasi | `config.ini` |
| `--dry-run` | Mode simulasi tanpa perubahan SAP | `False` |
| `--log-level` | Level log: DEBUG/INFO/WARNING/ERROR | `INFO` |

---

## Struktur Proyek

```
├── main.py                  # Entry point program
├── hapus_lo.py              # Logika inti otomatisasi SAP VL02N
├── config.py                # Pembaca konfigurasi
├── config.ini               # File konfigurasi
├── requirements.txt         # Dependensi Python
├── data/
│   └── daftar_lo_contoh.csv # Contoh file input
├── output/                  # Hasil proses (otomatis dibuat)
└── logs/                    # File log (otomatis dibuat)
```

---

## Output

Setelah proses selesai, file Excel hasil akan tersimpan di `output/hasil_hapus_lo.xlsx`:

| nomor_lo   | status        | pesan                                |
|------------|---------------|--------------------------------------|
| 0080012345 | BERHASIL      | Delivery 0080012345 saved            |
| 0080012346 | TIDAK DITEMUKAN | LO 0080012346 tidak ditemukan di SAP |
| 0080012347 | GAGAL         | Pesan error dari SAP                 |

---

## Lisensi

Hak Cipta © PT Pertamina Patra Niaga. Hanya untuk penggunaan internal.
