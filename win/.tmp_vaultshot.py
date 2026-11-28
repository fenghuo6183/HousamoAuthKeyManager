# -*- coding: utf-8 -*-
"""Render the vault page against a temporary account library."""

import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

base_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".tmp", "vdata"))
if os.path.isdir(base_dir):
    shutil.rmtree(base_dir)
os.makedirs(base_dir)
os.environ["HOUSAMO_DATA_DIR"] = base_dir
os.environ["HOUSAMO_NO_ADB"] = "1"
os.environ["HOUSAMO_NO_TRAY"] = "1"

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app import config, vault

settings = config.Settings()

for game_id, rows in (
    ("housamo", [("主账号", "AbCdEfGh1234567890aaaaaaaaaaaaaaaaaaaaaa"),
                 ("小号", "ZzYyXx9876543210bbbbbbbbbbbbbbbbbbbbbb")]),
    ("liveahero", [("Live 主号", "QqWwEe1122334455cccccccccccccccccccccc")]),
):
    box = vault.Vault(path=vault.vault_path_for(game_id), game_id=game_id)
    for index, (name, key) in enumerate(rows):
        entry, _created = box.add(name, key.encode(), source="测试", device="127.0.0.1:16384", game=game_id)
        entry["created_at"] = "2026-11-2%d 1%d:0%d:00" % (index + 1, index + 2, index + 3)
    box.save()

from qtui.pages import settings_page, tasks_page, vault_page
from qtui.window import Shell


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "../.tmp/vault.png"
    application = QApplication(sys.argv)
    shell = Shell(settings, live=True)
    shell.add_page("tasks", tasks_page(shell))
    shell.add_page("vault", vault_page(shell))
    shell.add_page("settings", settings_page(shell))
    shell.resize(1100, 900)
    shell.controller.boot()

    def snap():
        shell.show_page("vault")
        shell.resize(1100, 900)
        application.processEvents()
        shell.repaint()
        application.processEvents()
        shell.grab().save(out)
        service = shell.controller.service
        print("saved", out, "entries:", len(service.vault.entries) if service else -1, flush=True)
        application.quit()

    QTimer.singleShot(int(os.environ.get("SNAP_MS", "6000")), snap)
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
