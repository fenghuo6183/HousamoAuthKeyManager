# -*- coding: utf-8 -*-
"""Dump the live tasks page state as text (no eyeballing)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QLabel, QPlainTextEdit, QComboBox, QAbstractButton

from app import config
from qtui.pages import settings_page, tasks_page, vault_page
from qtui.window import Shell


def main():
    app = QApplication(sys.argv)
    settings = config.Settings()
    shell = Shell(settings, live=True)
    tasks = tasks_page(shell)
    shell.add_page("tasks", tasks)
    shell.add_page("vault", vault_page(shell))
    shell.add_page("settings", settings_page(shell))
    shell.resize(1100, 900)
    shell.show()
    shell.controller.boot()

    def dump():
        print("busy:", shell.controller.busy, flush=True)
        print("service:", bool(shell.controller.service), flush=True)
        if shell.controller.service:
            svc = shell.controller.service
            print("adb:", bool(svc.adb), svc.adb_error[:60], flush=True)
            print("devices:", [(d.serial, d.state) for d in svc.devices], flush=True)
            print("vault entries:", len(svc.vault.entries), "err:", svc.vault_error[:40], flush=True)
            print("serial:", svc.serial, flush=True)
        for label in tasks.findChildren(QLabel):
            text = label.text().strip()
            if text:
                print("LABEL:", text, flush=True)
        for box in tasks.findChildren(QComboBox):
            print("COMBO count:", box.count(), "text:", box.currentText(), "editable:", box.isEditable(), flush=True)
        for edit in tasks.findChildren(QPlainTextEdit):
            print("LOG:\n" + edit.toPlainText(), flush=True)
        for button in tasks.findChildren(QAbstractButton):
            if isinstance(button, QAbstractButton) and button.text():
                print("BUTTON:", button.text(), "enabled:", button.isEnabled(), flush=True)
        app.quit()

    QTimer.singleShot(7000, dump)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
