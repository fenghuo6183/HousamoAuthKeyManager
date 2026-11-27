import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-uil-")
os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk

from app import theme
from app import ui as ui_mod
from app.ui import App


class LanUiTest(unittest.TestCase):
    def setUp(self):
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-uil-")
        theme.set_ui_scale(1.0)
        self._saved = (ui_mod.messagebox.showinfo, ui_mod.messagebox.showerror,
                       ui_mod.messagebox.askyesno)
        self.shown = []
        ui_mod.messagebox.showinfo = lambda *a, **k: self.shown.append(a)
        ui_mod.messagebox.showerror = lambda *a, **k: self.shown.append(a)
        ui_mod.messagebox.askyesno = lambda *a, **k: True
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root)
        self.root.update()

    def tearDown(self):
        (ui_mod.messagebox.showinfo, ui_mod.messagebox.showerror,
         ui_mod.messagebox.askyesno) = self._saved
        try:
            self.app._on_lan_closed()
        except Exception:
            pass
        self.root.destroy()

    def test_empty_vault_shows_hint(self):
        self.app.open_lan_share()
        self.assertEqual(len(self.shown), 1)
        self.assertIn("空", str(self.shown[0]))

    def test_dialog_serves_accounts_and_stops_on_close(self):
        self.app._import_scanned([{"name": "主号", "key": b"lan-key-123456789"}],
                                 source="文件夹")
        self.app.open_lan_share()
        server = self.app.lan
        self.assertIsNotNone(server)
        self.assertTrue(self.app.lan_win.winfo_exists())
        rows = server.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["key"], "lan-key-123456789")
        url = server.url()
        self.assertIn("/?k=" + server.code, url)
        self.app.lan_win.destroy()
        self.root.update()
        self.assertIsNone(self.app.lan)

    def test_reopening_after_close_gets_new_server(self):
        self.app._import_scanned([{"name": "主号", "key": b"lan-key-abcdefghij"}],
                                 source="文件夹")
        self.app.open_lan_share()
        first = self.app.lan
        self.app.lan_win.destroy()
        self.root.update()
        self.app.open_lan_share()
        self.assertIsNot(self.app.lan, first)
        self.assertIsNone(first.httpd)


if __name__ == "__main__":
    unittest.main()
