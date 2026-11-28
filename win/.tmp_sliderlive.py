# -*- coding: utf-8 -*-
import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("HOUSAMO_NO_ADB", "1")
from PySide6.QtWidgets import QApplication, QSlider
from app import config
from qtui.pages import settings_page, tasks_page, vault_page
from qtui.window import Shell

app = QApplication(sys.argv)
settings = config.Settings()
settings.set("glass", 25, save=False)
shell = Shell(settings, live=True)
shell.add_page("tasks", tasks_page(shell))
shell.add_page("vault", vault_page(shell))
shell.add_page("settings", settings_page(shell))
shell.resize(1100, 900)
shell.show_page("settings")
shell.pages.currentWidget().select(1)
shell.show()
app.processEvents()

sliders = shell.pages.currentWidget().findChildren(QSlider)
print("sliders", [s.value() for s in sliders])
glass, blur = sliders[0], sliders[1]
print("before", round(shell._cards[0].alpha, 3), shell.backdrop.blur)
glass.setValue(100)
app.processEvents()
print("after glass drag", round(shell._cards[0].alpha, 3))
blur.setValue(30)
app.processEvents()
print("blur immediately", shell.backdrop.blur)
for _ in range(30):
    app.processEvents()
    time.sleep(0.02)
print("blur after 600ms", shell.backdrop.blur)
app.quit()
