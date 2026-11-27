import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-uiv-")
os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk

from app import theme
from app.ui import App

KEY_A = b"backup-key-0123456789-aaaa"
KEY_B = b"account-key-0123456789-bbbb"


class VaultSectionsTest(unittest.TestCase):
    def setUp(self):
        # 每个用例用全新的数据目录：active_game 会写进 settings.json
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-uiv-")
        theme.set_ui_scale(1.0)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root)
        self.root.update()

    def tearDown(self):
        self.root.destroy()

    def _add(self, key, kind):
        return self.app.vault.add(name="n", key=key, kind=kind)[0]

    def test_account_rows_only(self):
        self._add(KEY_B, "account")
        self._add(KEY_A, "backup")
        self.app.vault_kind = "account"
        self.app.refresh_vault()
        rows = self.app.vault_tree.get_children()
        self.assertEqual(len(rows), 1)

    def test_backup_rows(self):
        self._add(KEY_B, "account")
        self._add(KEY_A, "backup")
        self.app.vault_kind = "backup"
        self.app.refresh_vault()
        self.assertEqual(len(self.app.vault_tree.get_children()), 1)
        self.assertIn("备份", self.app.count_chip.cget("text"))

    def test_data_card_shows_current_game(self):
        self.app._refresh_data_card()
        self.assertIn("vault.housamo.dat", self.app.data_rows["vault"].cget("text"))
        self.app.switch_game("liveahero")
        self.assertIn("vault.liveahero.dat", self.app.data_rows["vault"].cget("text"))

    def test_long_cells_are_ellipsized_to_column_width(self):
        long_name = "一个特别特别长的账号名字用来测试省略号"
        entry = self._add(KEY_B, "account")
        entry["name"] = long_name
        self.app.refresh_vault()
        value = self.app.vault_tree.item(entry["id"], "values")[0]
        self.assertTrue(value.endswith("…"))
        width = int(self.app.vault_tree.column("name", "width"))
        self.assertLessEqual(self.app._cell_font().measure(value), width)

    def test_fingerprint_keeps_length_suffix_when_trimmed(self):
        entry = self._add(KEY_B, "account")
        entry["fingerprint"] = "ab12cd34ef56ab78cd90ef12ab34cd56ef78ab90 (128)"
        self.app.refresh_vault()
        value = self.app.vault_tree.item(entry["id"], "values")[2]
        self.assertTrue(value.endswith(" (128)"))
        self.assertIn("…", value)

    def test_export_goes_under_game_folder(self):
        self.app.save_dir = tempfile.mkdtemp()
        out = self.app.export_to_dir("acc", KEY_B)
        self.assertIsNotNone(out)
        rel = os.path.relpath(out, self.app.save_dir).replace("\\", "/")
        self.assertEqual(rel, "\u4e1c\u4eac\u653e\u8bfe\u540e/acc/AuthKey.txt")


if __name__ == "__main__":
    unittest.main()
