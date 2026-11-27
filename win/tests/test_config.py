import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-cfg-")

from app import config


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "settings.json")

    def test_new_defaults(self):
        s = config.Settings(self.path)
        self.assertEqual(s.get("active_game"), "housamo")
        self.assertEqual(s.get("update_source"), "auto")
        self.assertEqual(s.get("reconcile_ignored"), {})
        self.assertEqual(s.get("last_update_check"), 0)

    def test_bad_active_game_normalised(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write('{"active_game": "wildcard"}')
        self.assertEqual(config.Settings(self.path).get("active_game"), "housamo")

    def test_bad_update_source_normalised(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write('{"update_source": "ftp"}')
        self.assertEqual(config.Settings(self.path).get("update_source"), "auto")

    def test_ignore_table(self):
        s = config.Settings(self.path)
        self.assertFalse(config.is_reconcile_ignored(s, "housamo", "abc"))
        config.ignore_reconcile(s, "housamo", "abc")
        config.ignore_reconcile(s, "housamo", "abc")
        self.assertTrue(config.is_reconcile_ignored(s, "housamo", "abc"))
        self.assertEqual(s.get("reconcile_ignored")["housamo"], ["abc"])

    def test_data_dir_override(self):
        self.assertEqual(config.app_dir(), os.environ["HOUSAMO_DATA_DIR"])


if __name__ == "__main__":
    unittest.main()
