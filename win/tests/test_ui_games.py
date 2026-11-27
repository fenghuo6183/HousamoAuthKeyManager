import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-ui-")
os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk

from app import theme
from app.ui import App


class SwitchGameTest(unittest.TestCase):
    def setUp(self):
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-ui-")
        theme.set_ui_scale(1.0)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root)
        self.root.update()

    def tearDown(self):
        self.root.destroy()

    def test_default_is_housamo(self):
        self.assertEqual(self.app.active_game.id, "housamo")
        self.assertTrue(self.app.vault.path.endswith("vault.housamo.dat"))

    def test_switch_to_liveahero(self):
        self.app.switch_game("liveahero")
        self.assertEqual(self.app.active_game.id, "liveahero")
        self.assertTrue(self.app.vault.path.endswith("vault.liveahero.dat"))
        self.assertEqual(self.app.settings.get("active_game"), "liveahero")
        self.assertIn("LiveAHero", self.app.btn_extract.text)

    def test_switch_back_keeps_same_instance(self):
        first = self.app.vault
        self.app.switch_game("liveahero")
        self.app.switch_game("housamo")
        self.assertIs(self.app.vault, first)


if __name__ == "__main__":
    unittest.main()
