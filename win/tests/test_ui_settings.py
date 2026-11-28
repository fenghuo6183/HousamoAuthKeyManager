import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk

from app import adb, theme
from app.ui import App, EMULATOR_PORTS


def make_device(serial, model="", state="device"):
    return adb.Device(serial=serial, state=state, model=model)


class SettingsConnectionTest(unittest.TestCase):
    def setUp(self):
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-uiset-")
        theme.set_ui_scale(1.0)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root)
        self.root.update()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_connection_card_exists(self):
        self.assertIsNotNone(self.app.only_emu_seg)
        self.assertIsNotNone(self.app.auto_connect_seg)
        self.assertIsNotNone(self.app.ports_summary)
        self.assertIsNotNone(self.app.btn_edit_ports)
        self.assertIsNotNone(self.app.btn_rescan)

    def test_only_emulators_toggle_persists(self):
        self.app.only_emu_seg.select("on")
        self.assertTrue(self.app.settings.get("only_emulators"))

        self.app.only_emu_seg.select("off")
        self.assertFalse(self.app.settings.get("only_emulators"))

    def test_auto_connect_toggle_persists(self):
        self.app.auto_connect_seg.select("on")
        self.assertTrue(self.app.settings.get("auto_connect"))

    def test_ports_are_parsed_from_the_entry(self):
        self.app.ports_var.set("16384, 7555 ,x, 0")
        self.app._on_ports_change()

        self.assertEqual(self.app.emulator_ports(), [16384, 7555])

    def test_empty_ports_fall_back_to_the_defaults(self):
        self.app.ports_var.set("abc")
        self.app._on_ports_change()

        self.assertEqual(self.app.emulator_ports(), list(EMULATOR_PORTS))

    def test_forget_device_clears_the_preference(self):
        self.app.settings.set("preferred_serial", "127.0.0.1:16384")
        self.app.forget_device()

        self.assertEqual(self.app.settings.get("preferred_serial"), "")

    def test_about_row_shows_the_version(self):
        self.app._refresh_data_card()

        self.assertIn(theme.APP_VERSION, self.app.about_version_label.cget("text"))


if __name__ == "__main__":
    unittest.main()
