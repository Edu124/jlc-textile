import sys
import os
from PyQt6.QtWidgets import QApplication, QSplashScreen, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

import core.database as db
import core.pendrive as pendrive
from ui.styles import DARK


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("JLC Textile Manager")
    app.setApplicationVersion("1.0.0")
    app.setStyleSheet(DARK)

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    saved = pendrive.find_saved_drive()

    if saved:
        app_dir = saved.get("app_dir", "")
        drive_label = saved.get("label", saved.get("letter", "?") + ":\\")
        if os.path.isdir(app_dir):
            _launch_main(app, app_dir, drive_label)
            return

    _show_drive_selector(app)


def _show_drive_selector(app: QApplication):
    from ui.screens.drive_selector import DriveSelectorScreen
    screen = DriveSelectorScreen()
    screen.showMaximized()
    screen.setWindowTitle("JLC Textile Manager — Select Drive")

    def on_selected(app_dir: str, drive_path: str):
        drive_info = pendrive.get_removable_drives()
        label = drive_path
        for d in drive_info:
            if d["path"].rstrip("\\") == drive_path.rstrip("\\"):
                label = d["label"]
                break
        screen.close()
        _launch_main(app, app_dir, label)

    screen.drive_selected.connect(on_selected)
    app.exec()


def _launch_main(app: QApplication, app_dir: str, drive_label: str):
    db_path = pendrive.get_db_path(app_dir)
    db.init(db_path)

    from ui.main_window import MainWindow
    window = MainWindow(app_dir, drive_label)
    window.show()
    exit_code = app.exec()
    db.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
