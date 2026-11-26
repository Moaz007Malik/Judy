from __future__ import annotations
import sys, argparse
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtCore import Qt
from .config import Settings
from .ui import MainWindow, SetupWizard, STYLE, create_judy_icon
from .startup import set_launch_at_login

def main():
    parser = argparse.ArgumentParser(description="Judy Executive AI Desktop Assistant")
    parser.add_argument("--background", action="store_true", help="Launch directly in background tray")
    args, _ = parser.parse_known_args()

    # Create Qt App
    app = QApplication(sys.argv)
    app.setApplicationName("Judy")
    app.setOrganizationName("Judy")
    app.setWindowIcon(create_judy_icon())
    app.setQuitOnLastWindowClosed(False)

    settings = Settings.load()
    if not settings.setup_complete:
        wizard = SetupWizard(settings)
        if wizard.exec() != QDialog.DialogCode.Accepted:
            return 0
        wizard.apply()

    window = MainWindow(settings)
    window.setStyleSheet(STYLE)

    if args.background or settings.start_minimized:
        window.hide()
    else:
        window.show()

    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
