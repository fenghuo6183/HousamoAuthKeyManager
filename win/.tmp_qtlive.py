# -*- coding: utf-8 -*-
"""Headless smoke test for the live Qt shell: boots adb, grabs a screenshot."""

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
    app = QApplication(sys.argv)
    settings = config.Settings()
    shell = Shell(settings, live=True)
    shell.add_page("tasks", tasks_page(shell))
    shell.add_page("vault", vault_page(shell))
    shell.add_page("settings", settings_page(shell))
    shell.resize(1100, 900)
    shell.show()
    shell.controller.boot()

    seen = {"log": 0}

    def note(tag, message):
        seen["log"] += 1
        print("LOG", tag, message, flush=True)

    shell.controller.logged.connect(note)

    def snap():
        shell.repaint()
        app.processEvents()
        shell.grab().save(out)
        print("saved", out, shell.size().width(), shell.size().height(),
              "logs", seen["log"], flush=True)
        app.quit()

    QTimer.singleShot(int(os.environ.get("SNAP_MS", "7000")), snap)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
