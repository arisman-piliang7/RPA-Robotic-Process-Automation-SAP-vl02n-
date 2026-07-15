"""
hapus_lo.py
Modul inti otomatisasi penghapusan Loading Order (LO) di SAP VL02N
menggunakan SAP GUI Scripting API (win32com).
"""

import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

STATUS_BERHASIL = "BERHASIL"
STATUS_GAGAL = "GAGAL"
STATUS_TIDAK_DITEMUKAN = "TIDAK DITEMUKAN"
STATUS_SIMULASI = "SIMULASI"

# Kata kunci dalam pesan status SAP yang menandakan keberhasilan penghapusan
SUCCESS_KEYWORDS = [
    "saved",
    "disimpan",
    "deletion flag",
    "tanda hapus",
    "berhasil",
    "successfully",
    "gesetzt",
]


def hubungkan_sap(system_name: str) -> object:
    """
    Menghubungkan ke SAP GUI yang sedang berjalan dan mengembalikan
    objek Application SAP GUI.

    Raises:
        RuntimeError: Jika SAP GUI tidak ditemukan atau tidak berjalan.
    """
    try:
        import win32com.client
        sap_gui_auto = win32com.client.GetObject("SAPGUI")
        application = sap_gui_auto.GetScriptingEngine
        logger.info("Berhasil terhubung ke SAP GUI.")
        return application
    except Exception as exc:
        raise RuntimeError(
            "Tidak dapat terhubung ke SAP GUI. Pastikan SAP GUI sudah dibuka "
            "dan SAP GUI Scripting diaktifkan."
        ) from exc


def login_sap(
    application: object,
    system_name: str,
    client: str,
    username: str,
    password: str,
    language: str,
) -> object:
    """
    Login ke SAP menggunakan koneksi baru atau sesi yang sudah ada.

    Returns:
        Objek sesi SAP aktif.

    Raises:
        RuntimeError: Jika login gagal.
    """
    try:
        connection = application.OpenConnection(system_name, True)
        session = connection.Children(0)

        if session.Info.IsLowSpeedConnection:
            session.TestToolMode = 1

        session.findById("wnd[0]/usr/txtRSYST-MANDT").Text = client
        session.findById("wnd[0]/usr/txtRSYST-BNAME").Text = username
        session.findById("wnd[0]/usr/pwdRSYST-BCODE").Text = password
        session.findById("wnd[0]/usr/txtRSYST-LANGU").Text = language
        session.findById("wnd[0]").sendVKey(0)

        logger.info("Login SAP berhasil.")
        return session
    except Exception as exc:
        raise RuntimeError(f"Login SAP gagal: {exc}") from exc


def dapatkan_sesi_aktif(application: object) -> object:
    """
    Mengambil sesi SAP GUI yang sudah aktif tanpa login ulang.

    Returns:
        Objek sesi SAP aktif.

    Raises:
        RuntimeError: Jika tidak ada sesi aktif.
    """
    try:
        connection = application.Children(0)
        session = connection.Children(0)
        logger.info("Menggunakan sesi SAP yang sudah aktif.")
        return session
    except Exception as exc:
        raise RuntimeError(f"Tidak ada sesi SAP aktif: {exc}") from exc


def hapus_satu_lo(
    session: object,
    nomor_lo: str,
    delay: float = 1.0,
    dry_run: bool = False,
) -> dict:
    """
    Menghapus satu Loading Order (LO) melalui transaksi VL02N.

    Args:
        session: Objek sesi SAP GUI aktif.
        nomor_lo: Nomor LO yang akan dihapus (10 digit, contoh: 0080012345).
        delay: Waktu tunggu antar langkah (detik).
        dry_run: Jika True, proses hanya simulasi tanpa menyimpan perubahan.

    Returns:
        Dictionary berisi nomor_lo, status, dan pesan.
    """
    hasil = {"nomor_lo": nomor_lo, "status": STATUS_GAGAL, "pesan": ""}

    if dry_run:
        logger.info("[SIMULASI] LO %s akan dihapus (dry_run=True).", nomor_lo)
        hasil["status"] = STATUS_SIMULASI
        hasil["pesan"] = "Mode simulasi aktif, tidak ada perubahan di SAP."
        return hasil

    try:
        # Buka transaksi VL02N
        session.findById("wnd[0]").maximize()
        session.findById("wnd[0]/tbar[0]/okcd").Text = "/nvl02n"
        session.findById("wnd[0]").sendVKey(0)
        time.sleep(delay)

        # Masukkan nomor LO (Outbound Delivery Number)
        try:
            session.findById("wnd[0]/usr/ctxtLIKP-VBELN").Text = nomor_lo
        except Exception:
            hasil["status"] = STATUS_TIDAK_DITEMUKAN
            hasil["pesan"] = f"Field nomor LO tidak ditemukan di layar VL02N."
            logger.warning("Field nomor LO tidak ditemukan untuk LO: %s", nomor_lo)
            return hasil

        session.findById("wnd[0]").sendVKey(0)
        time.sleep(delay)

        # Periksa apakah LO ditemukan (cek status bar)
        status_bar = session.findById("wnd[0]/sbar").Text
        if "tidak ditemukan" in status_bar.lower() or "not found" in status_bar.lower():
            hasil["status"] = STATUS_TIDAK_DITEMUKAN
            hasil["pesan"] = f"LO {nomor_lo} tidak ditemukan di SAP."
            logger.warning("LO tidak ditemukan: %s | Status SAP: %s", nomor_lo, status_bar)
            return hasil

        # Tandai penghapusan melalui menu: Outbound Delivery -> Flag for Deletion
        # Menu path: Outbound Delivery > Flag for Deletion (fungsi F6 atau melalui menu)
        _tandai_hapus(session, delay)

        # Konfirmasi dialog penghapusan jika muncul
        _konfirmasi_dialog(session, delay)

        # Simpan
        session.findById("wnd[0]").sendVKey(11)  # Ctrl+S (Save)
        time.sleep(delay)

        # Verifikasi hasil
        pesan_sap = session.findById("wnd[0]/sbar").Text
        if _cek_berhasil(pesan_sap):
            hasil["status"] = STATUS_BERHASIL
            hasil["pesan"] = pesan_sap or f"LO {nomor_lo} berhasil ditandai untuk dihapus."
            logger.info("LO %s berhasil dihapus. Pesan SAP: %s", nomor_lo, pesan_sap)
        else:
            hasil["status"] = STATUS_GAGAL
            hasil["pesan"] = pesan_sap or "Tidak ada konfirmasi keberhasilan dari SAP."
            logger.error("LO %s gagal dihapus. Pesan SAP: %s", nomor_lo, pesan_sap)

    except Exception as exc:
        hasil["status"] = STATUS_GAGAL
        hasil["pesan"] = str(exc)
        logger.exception("Error saat memproses LO %s: %s", nomor_lo, exc)

    return hasil


def _tandai_hapus(session: object, delay: float) -> None:
    """
    Menandai LO untuk dihapus melalui menu SAP VL02N.
    Menggunakan menu Outbound Delivery > Flag for Deletion.
    """
    try:
        # Coba akses menu: Outbound Delivery (menu bar index 1) > Flag for Deletion
        session.findById("wnd[0]/mbar/menu[1]/menu[8]").select()
        time.sleep(delay)
    except Exception:
        # Fallback: gunakan shortcut keyboard jika menu tidak tersedia
        logger.debug("Menu Flag for Deletion tidak ditemukan, mencoba shortcut keyboard.")
        session.findById("wnd[0]").sendVKey(6)  # F6
        time.sleep(delay)


def _konfirmasi_dialog(session: object, delay: float) -> None:
    """Mengkonfirmasi dialog konfirmasi penghapusan jika muncul."""
    try:
        dialog = session.findById("wnd[1]")
        if dialog:
            # Klik tombol Yes/Ja/OK
            try:
                session.findById("wnd[1]/usr/btnSPOP-OPTION1").press()
            except Exception:
                session.findById("wnd[1]").sendVKey(0)
            time.sleep(delay)
    except Exception:
        pass  # Tidak ada dialog konfirmasi, lanjutkan


def _cek_berhasil(pesan_sap: str) -> bool:
    """Memeriksa apakah pesan status SAP menunjukkan keberhasilan."""
    pesan_lower = pesan_sap.lower()
    return any(kata in pesan_lower for kata in SUCCESS_KEYWORDS)


def logout_sap(session: object) -> None:
    """Logout dari SAP dan menutup sesi."""
    try:
        session.findById("wnd[0]/tbar[0]/okcd").Text = "/nex"
        session.findById("wnd[0]").sendVKey(0)
        logger.info("Logout SAP berhasil.")
    except Exception as exc:
        logger.warning("Peringatan saat logout SAP: %s", exc)
