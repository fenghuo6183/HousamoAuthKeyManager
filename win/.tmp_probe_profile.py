# -*- coding: utf-8 -*-
import os, sys, tempfile
os.environ.setdefault("HOUSAMO_DATA_DIR", tempfile.mkdtemp(prefix="hak-probe-"))
os.environ.setdefault("HOUSAMO_NO_ADB", "1")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PySide6.QtWidgets import QApplication
from app import config
from qtui.window import Shell
from qtui.pages import settings_page
from qtui.widgets import ChevronCombo

app = QApplication([])
settings = config.Settings()
settings.set("connect_profile", "auto")
settings.set("preferred_serial", "")
settings.set("emulator_ports", "16384,5555")
shell = Shell(settings, live=False)
page = settings_page(shell)
shell.add_page("settings", page)
shell.show_page("settings")
app.processEvents()
combos = page.findChildren(ChevronCombo)
print("combos", len(combos), [c.currentText() for c in combos])
profile, addr = combos[0], combos[1]
profile.setCurrentIndex(1)
app.processEvents()
print("mumu ->", repr(addr.currentText()), settings.get("connect_profile"), settings.get("emulator_ports"), settings.get("preferred_serial"))
profile.setCurrentIndex(4)
app.processEvents()
print("bst ->", repr(addr.currentText()), settings.get("preferred_serial"))
profile.setCurrentIndex(0)
app.processEvents()
print("auto ->", repr(addr.currentText()), repr(settings.get("preferred_serial")))
profile.setCurrentIndex(1)
app.processEvents()
profile.setCurrentIndex(5)
app.processEvents()
print("custom keeps", repr(addr.currentText()), settings.get("connect_profile"))
