import ctypes
import string
import os
import json

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".jlc_textile", "config.json")
APP_FOLDER = "JLC_TextileManager"


def get_removable_drives():
    drives = []
    try:
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drive = f"{letter}:\\"
                drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive)
                if drive_type == 2:  # DRIVE_REMOVABLE
                    try:
                        label = _get_volume_label(drive)
                        free = _get_free_space(drive)
                        serial = _get_volume_serial(drive)
                        drives.append({
                            "path": drive,
                            "label": label or f"Drive {letter}",
                            "letter": letter,
                            "free_gb": round(free / (1024 ** 3), 1),
                            "serial": serial
                        })
                    except Exception:
                        drives.append({
                            "path": drive,
                            "label": f"Drive {letter}",
                            "letter": letter,
                            "free_gb": 0,
                            "serial": ""
                        })
            bitmask >>= 1
    except Exception:
        pass
    return drives


def _get_volume_label(drive):
    buf = ctypes.create_unicode_buffer(256)
    ctypes.windll.kernel32.GetVolumeInformationW(
        drive, buf, 256, None, None, None, None, 0
    )
    return buf.value


def _get_free_space(drive):
    free_bytes = ctypes.c_ulonglong(0)
    ctypes.windll.kernel32.GetDiskFreeSpaceExW(
        drive, ctypes.byref(free_bytes), None, None
    )
    return free_bytes.value


def _get_volume_serial(drive):
    serial = ctypes.c_ulong(0)
    ctypes.windll.kernel32.GetVolumeInformationW(
        drive, None, 0, ctypes.byref(serial), None, None, None, 0
    )
    return str(serial.value)


def setup_drive_folder(drive_path: str) -> str:
    app_dir = os.path.join(drive_path, APP_FOLDER)
    for sub in ["images/products", "images/raw_materials", "images/ai_designs",
                "bills/purchase", "bills/sales", "backups"]:
        os.makedirs(os.path.join(app_dir, sub), exist_ok=True)
    return app_dir


def save_config(drive_path: str, serial: str):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    data = {"drive_path": drive_path, "serial": serial,
            "app_dir": os.path.join(drive_path, APP_FOLDER)}
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f)


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return {}
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def find_saved_drive() -> dict:
    config = load_config()
    if not config:
        return {}
    saved_serial = config.get("serial", "")
    if not saved_serial:
        return {}
    for drive in get_removable_drives():
        if drive["serial"] == saved_serial:
            return {**config, **drive}
    return {}


def get_db_path(app_dir: str) -> str:
    return os.path.join(app_dir, "database.db")
