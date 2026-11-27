import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk

from app import applock, theme
from app.ui import App


class LockRowTest(unittest.TestCase):
    def setUp(self):
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-uil-")
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

    def test_row_starts_off(self):
        self.app._refresh_data_card()
        self.assertEqual(self.app.lock_value.cget("text"), "未开启")
        self.assertEqual(self.app.btn_lock.text, "开启")

    def test_row_follows_settings(self):
        applock.set_pin(self.app.settings, "1357")
        self.app._refresh_data_card()
        self.assertIn("已开启", self.app.lock_value.cget("text"))
        self.assertEqual(self.app.btn_lock.text, "关闭")
        applock.clear_pin(self.app.settings)
        self.app._refresh_data_card()
        self.assertEqual(self.app.btn_lock.text, "开启")

    def test_theme_rebuild_keeps_row(self):
        applock.set_pin(self.app.settings, "1357")
        self.app._apply_theme("dark")
        self.root.update()
        self.app._refresh_data_card()
        self.assertIn("已开启", self.app.lock_value.cget("text"))
        self.assertEqual(self.app.btn_lock.text, "关闭")
        self.assertEqual(self.app.pal["window"], theme.DARK["window"])


if __name__ == "__main__":
    unittest.main()
