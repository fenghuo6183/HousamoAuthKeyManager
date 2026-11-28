# -*- coding: utf-8 -*-
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("HOUSAMO_NO_ADB", "1")
from PySide6.QtWidgets import QApplication
from app import config
from qtui.pages import settings_page, tasks_page, vault_page
from qtui.window import Shell

app = QApplication(sys.argv)
settings = config.Settings()
shell = Shell(settings, live=True)
shell.add_page("tasks", tasks_page(shell))
shell.add_page("vault", vault_page(shell))
shell.add_page("settings", settings_page(shell))
shell.resize(1100, 900)
shell.show()
app.processEvents()
for blur in (0, 12, 30, 40):
    t = time.perf_counter()
    shell.set_backdrop(blur=blur, save=False)
    shell.backdrop.pixmap()
    app.processEvents()
    print("blur", blur, "%.0f ms" % ((time.perf_counter() - t) * 1000))
app.quit()
