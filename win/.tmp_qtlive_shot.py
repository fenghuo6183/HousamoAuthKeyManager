# -*- coding: utf-8 -*-
"""Live shell screenshot without mapping a window (screen-size independent)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app import config
from qtui.pages import settings_page, tasks_page, vault_page
from qtui.window import Shell


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "../.tmp/qtlive.png"
    page = sys.argv[2] if len(sys.argv) > 2 else "tasks"
    app = QApplication(sys.argv)
    settings = config.Settings()
    if os.environ.get("SNAP_THEME"):
        settings.set("theme", os.environ["SNAP_THEME"], save=False)
    if os.environ.get("SNAP_GLASS"):
        settings.set("glass", int(os.environ["SNAP_GLASS"]), save=False)
    shell = Shell(settings, live=True)
    shell.add_page("tasks", tasks_page(shell))
    shell.add_page("vault", vault_page(shell))
    shell.add_page("settings", settings_page(shell))
    shell.resize(1100, 900)
    shell.controller.boot()

    def snap():
        shell.show_page(page)
        if os.environ.get("SNAP_SECTION") and page == "settings":
            settings_widget = shell.pages.currentWidget()
            index = int(os.environ["SNAP_SECTION"])
            if hasattr(settings_widget, "select"):
                settings_widget.select(index)
        shell.resize(1100, 900)
        app.processEvents()
        shell.repaint()
        app.processEvents()
        shell.grab().save(out)
        print("saved", out, shell.size().width(), shell.size().height(), flush=True)
        app.quit()

    QTimer.singleShot(int(os.environ.get("SNAP_MS", "7000")), snap)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
