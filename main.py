"""
main.py
Titik masuk (entry point) otomatisasi penghapusan Loading Order (LO)
di SAP VL02N untuk PT Pertamina Patra Niaga.

Cara penggunaan:
    python main.py
    python main.py --config config.ini
    python main.py --config config.ini --dry-run
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime

import pandas as pd
from openpyxl.styles import numbers as xl_numbers

from config import load_config, get_sap_config, get_file_config, get_settings
from hapus_lo import (
    hubungkan_sap,
    login_sap,
    dapatkan_sesi_aktif,
    hapus_satu_lo,
    logout_sap,
    STATUS_BERHASIL,
)

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO") -> None:
    """Mengatur konfigurasi logging ke konsol dan file."""
    os.makedirs("logs", exist_ok=True)
    log_filename = os.path.join(
        "logs",
        f"hapus_lo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
    )
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_filename, encoding="utf-8"),
        ],
    )
    logging.info("Logging diinisialisasi. File log: %s", log_filename)


def baca_daftar_lo(file_config: dict) -> list:
    """
    Membaca daftar nomor LO dari file Excel atau CSV.

    Returns:
        List nomor LO sebagai string.

    Raises:
        FileNotFoundError: Jika file input tidak ditemukan.
        ValueError: Jika kolom nomor LO tidak ditemukan di file.
    """
    input_file = file_config["input_file"]
    kolom = file_config["kolom_nomor_lo"]

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"File input tidak ditemukan: {input_file}")

    if input_file.lower().endswith(".csv"):
        df = pd.read_csv(input_file, dtype=str)
    else:
        sheet = file_config.get("sheet_name") or "Sheet1"
        df = pd.read_excel(input_file, sheet_name=sheet, dtype=str)

    if kolom not in df.columns:
        raise ValueError(
            f"Kolom '{kolom}' tidak ditemukan di file. "
            f"Kolom yang tersedia: {list(df.columns)}"
        )

    daftar = df[kolom].dropna().str.strip().tolist()
    logging.info("Ditemukan %d nomor LO dari file: %s", len(daftar), input_file)
    return daftar


def simpan_hasil(hasil_list: list, output_file: str) -> None:
    """Menyimpan hasil proses ke file Excel dengan format teks untuk nomor LO."""
    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    df_hasil = pd.DataFrame(hasil_list, columns=["nomor_lo", "status", "pesan"])
    # Pastikan nomor_lo disimpan sebagai teks agar leading zero tidak hilang
    df_hasil["nomor_lo"] = df_hasil["nomor_lo"].astype(str)
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df_hasil.to_excel(writer, index=False, sheet_name="Hasil")
        workbook = writer.book
        worksheet = writer.sheets["Hasil"]
        # Atur format kolom nomor_lo sebagai teks
        for cell in worksheet.iter_cols(min_row=2, min_col=1, max_col=1, values_only=False):
            for c in cell:
                c.number_format = "@"
    logging.info("Hasil disimpan ke: %s", output_file)


def cetak_ringkasan(hasil_list: list) -> None:
    """Mencetak ringkasan hasil ke konsol."""
    total = len(hasil_list)
    berhasil = sum(1 for h in hasil_list if h["status"] == STATUS_BERHASIL)
    gagal = total - berhasil
    print("\n" + "=" * 50)
    print("RINGKASAN HASIL PENGHAPUSAN LO")
    print("=" * 50)
    print(f"Total LO diproses : {total}")
    print(f"Berhasil          : {berhasil}")
    print(f"Gagal/Lainnya     : {gagal}")
    print("=" * 50)


def parse_args() -> argparse.Namespace:
    """Memproses argumen baris perintah."""
    parser = argparse.ArgumentParser(
        description="Otomatisasi penghapusan LO di SAP VL02N (PT Pertamina Patra Niaga)"
    )
    parser.add_argument(
        "--config",
        default="config.ini",
        help="Path ke file konfigurasi (default: config.ini)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mode simulasi: tidak melakukan perubahan di SAP",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Level logging (default: INFO)",
    )
    return parser.parse_args()


def main() -> None:
    """Fungsi utama: membaca konfigurasi, login SAP, dan memproses penghapusan LO."""
    args = parse_args()
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)

    # Muat konfigurasi
    config = load_config(args.config)
    sap_config = get_sap_config(config)
    file_config = get_file_config(config)
    settings = get_settings(config)

    # Opsi dry-run dari argumen lebih diutamakan
    if args.dry_run:
        settings["dry_run"] = True

    dry_run = settings["dry_run"]
    delay = settings["delay"]
    max_retry = settings["max_retry"]

    if dry_run:
        logger.info("MODE SIMULASI (dry_run) AKTIF — tidak ada perubahan di SAP.")

    # Baca daftar LO
    try:
        daftar_lo = baca_daftar_lo(file_config)
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Gagal membaca daftar LO: %s", exc)
        sys.exit(1)

    if not daftar_lo:
        logger.warning("Daftar LO kosong. Program selesai.")
        sys.exit(0)

    # Koneksi SAP (dilewati pada mode simulasi)
    session = None
    hasil_list = []

    try:
        if not dry_run:
            application = hubungkan_sap(sap_config["system_name"])

            # Coba gunakan sesi aktif; jika gagal, login baru
            try:
                session = dapatkan_sesi_aktif(application)
            except RuntimeError:
                logger.info("Tidak ada sesi aktif, melakukan login SAP.")
                session = login_sap(
                    application,
                    sap_config["system_name"],
                    sap_config["client"],
                    sap_config["username"],
                    sap_config["password"],
                    sap_config["language"],
                )

        # Proses setiap LO
        for i, nomor_lo in enumerate(daftar_lo, start=1):
            logger.info("Memproses LO %d/%d: %s", i, len(daftar_lo), nomor_lo)
            for percobaan in range(1, max_retry + 1):
                hasil = hapus_satu_lo(session, nomor_lo, delay=delay, dry_run=dry_run)
                if hasil["status"] != "GAGAL":
                    break
                if percobaan < max_retry:
                    logger.warning(
                        "Percobaan %d gagal untuk LO %s. Mencoba ulang...",
                        percobaan,
                        nomor_lo,
                    )
                    time.sleep(delay * 2)
            hasil_list.append(hasil)

        cetak_ringkasan(hasil_list)

    except RuntimeError as exc:
        logger.error("Error koneksi SAP: %s", exc)
        sys.exit(1)
    finally:
        if session and not dry_run:
            try:
                logout_sap(session)
            except Exception:
                pass
        if hasil_list:
            simpan_hasil(hasil_list, file_config["output_file"])


if __name__ == "__main__":
    main()
