import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk

from app import theme
from app.widgets import Segmented


class SegmentedTest(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        theme.set_ui_scale(1.0)
        self.app = types.SimpleNamespace(pal=theme.PALETTE)
        self.hits = []

    def tearDown(self):
        self.root.destroy()

    def test_switch_and_callback(self):
        seg = Segmented(self.app, self.root, [("a", "A"), ("b", "B")],
                        active="a", command=self.hits.append)
        self.assertEqual(seg.active, "a")
        seg.select("b")
        self.assertEqual(seg.active, "b")
        self.assertEqual(self.hits, ["b"])
        seg.select("b")
        self.assertEqual(self.hits, ["b"])  # 重复点击不回调

    def test_set_active_silent(self):
        seg = Segmented(self.app, self.root, [("a", "A"), ("b", "B")], active="a")
        seg.set_active("b")
        self.assertEqual(seg.active, "b")

    def test_set_text(self):
        seg = Segmented(self.app, self.root, [("a", "A")])
        seg.set_text("a", "hello")
        self.assertEqual(seg.labels["a"].cget("text"), "hello")


if __name__ == "__main__":
    unittest.main()
