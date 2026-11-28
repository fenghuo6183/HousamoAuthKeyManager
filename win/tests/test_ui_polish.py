# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk

from app import bulk, theme
from app.ui import App


class PolishTest(unittest.TestCase):
    def setUp(self):
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-pol-")
        theme.set_ui_scale(1.0)
        self.root = tk.Tk()
        self.root.geometry("1100x900")
        self.root.deiconify()
        self.app = App(self.root)
        self.root.update_idletasks()
        self.root.update()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def _settle(self, page, rounds=25):
        self.app._show_page(page)
        for _ in range(rounds):
            self.root.update()

    def test_brand_title_is_not_clipped_by_the_rail(self):
        self._settle("tasks")
        for widget in (self.app._brand_title, self.app._brand_sub):
            self.assertGreaterEqual(
                widget.winfo_width(), widget.winfo_reqwidth(),
                "brand text is clipped: %s" % widget.cget("text"))

    def test_overflowing_page_shows_a_scrollbar(self):
        self._settle("settings")
        self.assertGreater(self.app._overflow, 0)
        self.assertTrue(self.app.page_scroll.winfo_ismapped())

    def test_short_page_hides_the_scrollbar(self):
        self._settle("tasks")
        self.assertEqual(self.app._overflow, 0)
        self.assertFalse(self.app.page_scroll.winfo_ismapped())

    def test_recent_imports_list_is_on_the_task_page(self):
        specs = self.app.pages["tasks"]
        self.assertEqual(len(specs), 2)
        self.assertIsNone(specs[1][1])

    def test_recent_imports_shows_the_last_import(self):
        bulk.record_import(self.app.settings, self.app.active_game.id,
                           {"id": "e1", "name": "\u4e3b\u53f7", "fingerprint": "abcdef012345"})
        self.app.refresh_overview()
        self.root.update()
        texts = [row.cget("text") for row in self.app.recent_rows]
        self.assertTrue(any("\u4e3b\u53f7" in t for t in texts), texts)

    def test_recent_imports_hint_when_empty(self):
        self.app.refresh_overview()
        self.root.update()
        self.assertEqual(self.app.recent_rows, [])
        self.assertIn("\u8fd8\u6ca1\u6709\u5bfc\u5165\u8bb0\u5f55",
                      self.app.recent_empty.cget("text"))


if __name__ == "__main__":
    unittest.main()
