import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk

from app import dialogs, theme
from app.ui import App


class TextDialogTest(unittest.TestCase):
    def setUp(self):
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-uidlg-")
        theme.set_ui_scale(1.0)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root)
        self.root.update()
        self.dialogs = []

    def tearDown(self):
        for dlg in self.dialogs:
            try:
                dlg.close()
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def _open(self, **kwargs):
        dlg = dialogs.TextDialog(self.app, **kwargs)
        self.dialogs.append(dlg)
        self.root.update()
        return dlg

    def test_save_returns_typed_text(self):
        dlg = self._open(title="重命名", initial="旧名字")
        dlg.var.set("  新名字  ")
        dlg.ok()

        self.assertEqual(dlg.result, "新名字")

    def test_cancel_returns_none(self):
        dlg = self._open(title="重命名", initial="旧名字")
        dlg.var.set("改了一半")
        dlg.cancel()

        self.assertIsNone(dlg.result)

    def test_blank_name_is_rejected(self):
        dlg = self._open(title="重命名")
        dlg.var.set("   ")
        dlg.ok()

        self.assertIsNone(dlg.result)
        self.assertTrue(dlg.window.winfo_exists())
        self.assertTrue(dlg.error_label.cget("text"))

    def test_duplicate_name_is_rejected_with_a_hint(self):
        dlg = self._open(title="重命名", taken=["阿一", "阿二"])
        dlg.var.set("阿一")
        dlg.ok()

        self.assertIsNone(dlg.result)
        self.assertIn("已经有", dlg.error_label.cget("text"))

    def test_too_long_name_is_rejected(self):
        dlg = self._open(title="重命名", max_len=4)
        dlg.var.set("一二三四五")
        dlg.ok()

        self.assertIsNone(dlg.result)

    def test_counter_tracks_length(self):
        dlg = self._open(title="重命名", max_len=20, initial="abc")

        self.assertIn("3", dlg.counter_label.cget("text"))

    def test_note_dialog_reads_multiline_text(self):
        dlg = self._open(title="编辑备注", multiline=True, initial="第一行")
        dlg.text_widget.delete("1.0", "end")
        dlg.text_widget.insert("1.0", "第一行\n第二行")
        dlg.ok()

        self.assertEqual(dlg.result, "第一行\n第二行")


if __name__ == "__main__":
    unittest.main()
