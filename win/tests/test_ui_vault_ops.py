import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk

from app import theme
from app.ui import App

KEY = "0123456789abcdef" * 9


class VaultOpsTest(unittest.TestCase):
    def setUp(self):
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-vops-")
        theme.set_ui_scale(1.0)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root)
        self.root.update()
        self.app._show_page("vault")
        self.root.update()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def _entry(self, name="\u4e3b\u53f7"):
        entry, _created = self.app.vault.add(name=name, key=KEY.encode("utf-8"),
                                             source="\u6d4b\u8bd5", kind="account")
        self.app.refresh_vault()
        self.root.update()
        return entry

    def test_f2_is_bound_to_rename(self):
        script = self.app.vault_tree.bind("<F2>")
        self.assertTrue(script)
        self.assertIn("_on_vault_f2", script)

    def test_f2_renames_the_selected_row(self):
        entry = self._entry()
        self.app.vault_tree.selection_set(entry["id"])
        called = []
        original = self.app.rename_entry
        self.app.rename_entry = lambda: called.append(True)
        try:
            self.app._on_vault_f2()
        finally:
            self.app.rename_entry = original
        self.assertEqual(called, [True])

    def test_f2_without_selection_does_not_rename(self):
        called = []
        original = self.app.rename_entry
        self.app.rename_entry = lambda: called.append(True)
        try:
            self.app._on_vault_f2()
        finally:
            self.app.rename_entry = original
        self.assertEqual(called, [])

    def test_new_entry_is_revealed_in_vault(self):
        entry = self._entry()
        self.app._show_page("tasks")
        self.root.update()

        self.app.reveal_entry(entry["id"])
        self.root.update()

        self.assertEqual(self.app.page, "vault")
        self.assertIn(entry["id"], self.app.vault_tree.selection())
        self.assertIn("flash", self.app.vault_tree.item(entry["id"], "tags"))

    def test_flash_tag_can_be_cleared(self):
        entry = self._entry()
        self.app.reveal_entry(entry["id"])
        self.root.update()
        self.app.clear_flash(entry["id"])
        self.root.update()
        self.assertNotIn("flash", self.app.vault_tree.item(entry["id"], "tags"))


if __name__ == "__main__":
    unittest.main()
