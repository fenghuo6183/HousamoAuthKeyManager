import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk

from app import dnd, theme
from app.ui import App


class DropPathsTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="hak-dnd-")
        self.good = os.path.join(self.dir, "\u53f7.hak")
        self.good2 = os.path.join(self.dir, "two.HAK")
        self.txt = os.path.join(self.dir, "notes.txt")
        for path in (self.good, self.good2, self.txt):
            with open(path, "wb") as fh:
                fh.write(b"x")

    def test_only_existing_hak_files_survive(self):
        missing = os.path.join(self.dir, "nope.hak")
        picked = dnd.hak_paths([self.good, self.txt, missing, self.good2])
        self.assertEqual(picked, [self.good, self.good2])

    def test_empty_and_odd_input(self):
        self.assertEqual(dnd.hak_paths([]), [])
        self.assertEqual(dnd.hak_paths(["", "  "]), [])


class DropHandlerTest(unittest.TestCase):
    def setUp(self):
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-dndh-")
        theme.set_ui_scale(1.0)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root)
        self.root.update()
        self.dir = tempfile.mkdtemp(prefix="hak-dnd2-")

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def _file(self, name):
        path = os.path.join(self.dir, name)
        with open(path, "wb") as fh:
            fh.write(b"x")
        return path

    def test_dropped_hak_files_are_imported_one_by_one(self):
        paths = [self._file("a.hak"), self._file("b.hak"), self._file("c.txt")]
        seen = []
        original = self.app._import_hak_path
        self.app._import_hak_path = lambda path: seen.append(path)
        try:
            self.app.handle_dropped_files(paths)
        finally:
            self.app._import_hak_path = original
        self.assertEqual(len(seen), 2)

    def test_dropping_nothing_useful_just_logs(self):
        seen = []
        original = self.app._import_hak_path
        self.app._import_hak_path = lambda path: seen.append(path)
        try:
            self.app.handle_dropped_files([self._file("c.txt")])
        finally:
            self.app._import_hak_path = original
        self.assertEqual(seen, [])


if __name__ == "__main__":
    unittest.main()
