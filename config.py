"""
config.py
Modul untuk membaca konfigurasi dari file config.ini.
"""

import configparser
import os
import logging

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.ini")


def load_config(config_path: str = CONFIG_FILE) -> configparser.ConfigParser:
    """Membaca dan mengembalikan konfigurasi dari file config.ini."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"File konfigurasi tidak ditemukan: {config_path}"
        )
    config = configparser.ConfigParser()
    config.read(config_path, encoding="utf-8")
    logger.debug("Konfigurasi berhasil dimuat dari: %s", config_path)
    return config


def get_sap_config(config: configparser.ConfigParser) -> dict:
    """Mengembalikan konfigurasi SAP sebagai dictionary."""
    password = os.environ.get("SAP_PASSWORD") or config.get("SAP", "password", fallback="")
    if not password:
        raise ValueError(
            "Password SAP tidak ditemukan. Set environment variable SAP_PASSWORD."
        )
    return {
        "system_name": config.get("SAP", "system_name"),
        "client": config.get("SAP", "client"),
        "username": os.environ.get("SAP_USERNAME") or config.get("SAP", "username"),
        "password": password,
        "language": config.get("SAP", "language"),
    }


def get_file_config(config: configparser.ConfigParser) -> dict:
    """Mengembalikan konfigurasi file input/output sebagai dictionary."""
    return {
        "input_file": config.get("FILE", "input_file"),
        "sheet_name": config.get("FILE", "sheet_name", fallback="Sheet1"),
        "kolom_nomor_lo": config.get("FILE", "kolom_nomor_lo"),
        "output_file": config.get("FILE", "output_file"),
    }


def get_settings(config: configparser.ConfigParser) -> dict:
    """Mengembalikan pengaturan umum sebagai dictionary."""
    return {
        "delay": config.getfloat("SETTINGS", "delay", fallback=1.0),
        "max_retry": config.getint("SETTINGS", "max_retry", fallback=3),
        "dry_run": config.getboolean("SETTINGS", "dry_run", fallback=False),
    }
