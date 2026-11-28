import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk
import tkinter.font as tkfont

from app import theme
from app.ui import App


class PageLayoutTest(unittest.TestCase):
    def setUp(self):
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-lay-")
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

    def _body(self, page):
        return self.app.pages[page][0][0].body

    def test_body_children_stay_inside_the_card(self):
        for page in ("vault", "settings", "tasks"):
            self._settle(page)
            body = self._body(page)
            width = body.winfo_width()
            for child in body.winfo_children():
                if child.winfo_width() <= 1:
                    continue
                self.assertLessEqual(
                    child.winfo_x() + child.winfo_width(), width + 1,
                    "%s: %s sticks out of the card" % (page, child))

    def test_stacked_rows_do_not_overlap(self):
        for page in ("vault", "settings", "tasks"):
            self._settle(page)
            rows = [c for c in self._body(page).winfo_children()
                    if c.winfo_height() > 2 and c.winfo_width() > 2]
            rows.sort(key=lambda c: c.winfo_y())
            for upper, lower in zip(rows, rows[1:]):
                self.assertGreaterEqual(
                    lower.winfo_y(), upper.winfo_y() + upper.winfo_height() - 1,
                    "%s: rows overlap (%s over %s)"
                    % (page, upper, lower))

    def test_vault_header_search_field_has_room(self):
        self._settle("vault")
        self.assertGreaterEqual(self.app.vault_search.winfo_width(),
                                theme.px(150))

    def test_vault_toolbar_rows_fit(self):
        self._settle("vault")
        body = self._body("vault")
        width = body.winfo_width()
        for row in self.app.vault_toolbars:
            last = 0
            for child in row.winfo_children():
                last = max(last, child.winfo_x() + child.winfo_width())
            self.assertLessEqual(last, width + 1, "toolbar row overflows")

    def test_scan_ports_summary_fits_its_card(self):
        self._settle("settings")
        summary = self.app.ports_summary
        self.assertIn("\u7aef\u53e3", summary.cget("text"))
        self.assertGreaterEqual(summary.winfo_width(), summary.winfo_reqwidth())


if __name__ == "__main__":
    unittest.main()
