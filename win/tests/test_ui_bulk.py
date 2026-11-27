import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-uib-")
os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk

from app import bulk
from app import theme
from app import ui as ui_mod
from app.ui import App

KEY_A = b"bulk-key-0123456789-aaaa"
KEY_B = b"bulk-key-0123456789-bbbb"


def items(*keys):
    return [{"name": "账号 %d" % i, "key": k, "fingerprint": "fp%d" % i}
            for i, k in enumerate(keys)]


class BulkUiTest(unittest.TestCase):
    def setUp(self):
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-uib-")
        theme.set_ui_scale(1.0)
        self._saved = (ui_mod.messagebox.askyesno, ui_mod.messagebox.showinfo,
                       ui_mod.messagebox.showerror, ui_mod.filedialog.asksaveasfilename)
        self.asked = []
        ui_mod.messagebox.askyesno = lambda *a, **k: True
        ui_mod.messagebox.showinfo = lambda *a, **k: None
        ui_mod.messagebox.showerror = lambda *a, **k: None
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root)
        self.root.update()

    def tearDown(self):
        (ui_mod.messagebox.askyesno, ui_mod.messagebox.showinfo,
         ui_mod.messagebox.showerror, ui_mod.filedialog.asksaveasfilename) = self._saved
        self.root.destroy()

    def test_import_scanned_fills_table_and_counts(self):
        self.app._import_scanned(items(KEY_A, KEY_B), source="文件夹")
        self.assertEqual(len(self.app.vault_tree.get_children()), 2)
        self.assertEqual(len(self.app.vault.by_kind("account")), 2)
        self.assertEqual(self.app.stat_labels["accounts"].cget("text"), "2")
        self.assertEqual(self.app.vault.by_kind("account")[0]["source"], "文件夹")

    def test_import_scanned_skips_duplicates(self):
        self.app._import_scanned(items(KEY_A), source="剪贴板")
        self.app._import_scanned(items(KEY_A), source="剪贴板")
        self.assertEqual(len(self.app.vault.by_kind("account")), 1)

    def test_import_scanned_ignores_empty_result(self):
        self.app._import_scanned([], source="文件夹")
        self.assertEqual(len(self.app.vault.by_kind("account")), 0)

    def test_undo_last_import_removes_entry_and_history(self):
        self.app._import_scanned(items(KEY_A), source="文件夹")
        entry = self.app.vault.by_kind("account")[0]
        bulk.record_import(self.app.settings, self.app.active_game.id, entry)
        self.app._refresh_import_history()
        self.assertIn("上次导入", self.app.vault_history_label.cget("text"))
        self.app.undo_last_import()
        self.assertEqual(self.app.vault.by_kind("account"), [])
        self.assertIsNone(bulk.last_import(self.app.settings, self.app.active_game.id))
        self.assertEqual(self.app.vault_history_label.cget("text"), "还没有导入记录")

    def test_export_bundle_writes_zip(self):
        self.app.vault.add(name="导出我", key=KEY_A)
        target = os.path.join(tempfile.mkdtemp(), "bundle.zip")
        ui_mod.filedialog.asksaveasfilename = lambda *a, **k: target
        self.app.export_bundle()
        self.assertTrue(os.path.exists(target))
        with zipfile.ZipFile(target) as zf:
            self.assertIn("导出我/AuthKey.txt", zf.namelist())

    def test_backup_keep_policy_prunes_and_persists(self):
        for n in range(12):
            self.app.vault.add(name="备份 %d" % n, key=KEY_A + str(n).encode(), kind="backup")
        self.app._on_backup_keep("10")
        self.assertEqual(len(self.app.vault.by_kind("backup")), 10)
        self.assertEqual(self.app.settings.get("backup_keep"), "10")

    def test_overview_shows_counts(self):
        self.app.vault.add(name="a", key=KEY_A)
        self.app.vault.add(name="b", key=KEY_B, kind="backup")
        self.app.refresh_overview()
        self.assertEqual(self.app.stat_labels["accounts"].cget("text"), "1")
        self.assertEqual(self.app.stat_labels["backups"].cget("text"), "1")
        self.assertEqual(self.app.stat_labels["game_key"].cget("text"), "—")


if __name__ == "__main__":
    unittest.main()
