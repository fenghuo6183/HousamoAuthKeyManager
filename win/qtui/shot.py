"""Render the Qt shell offscreen for design review: python qtui/shot.py out.png page glass."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app import config
from qtui.pages import settings_page, tasks_page, vault_page
from qtui.window import Shell


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "../.tmp/qt_shell.png"
    page = sys.argv[2] if len(sys.argv) > 2 else "tasks"
    glass = float(sys.argv[3]) if len(sys.argv) > 3 else None

    app = QApplication(sys.argv)
    data_dir = os.environ.get("HOUSAMO_DATA_DIR")
    settings = config.Settings()
    shell = Shell(settings)
    shell.add_page("tasks", tasks_page(shell))
    shell.add_page("vault", vault_page(shell))
    shell.add_page("settings", settings_page(shell))
    if glass is not None:
        shell.set_glass(glass)
    shell.show_page(page)
    shell.resize(1100, 900)
    app.processEvents()
    shell.repaint()
    app.processEvents()
    shell.grab().save(out)
    print("saved", out, shell.size().width(), shell.size().height())


if __name__ == "__main__":
    main()
