import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-bulk-")

from app import bulk
from app import config
from app import vault

KEY = b"housamo-test-key-0123456789-abcdef"


def key(n):
    return ("housamo-test-key-%02d" % n).encode()


class BulkImportTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.mkdtemp(prefix="bulk-")
        self.vault = vault.Vault(os.path.join(tmp, "vault.housamo.dat"), game_id="housamo")
        self.settings = config.Settings(os.path.join(tmp, "settings.json"))

    def test_import_items_adds_new_and_skips_duplicates(self):
        items = [{"name": "A", "key": KEY}, {"name": "A again", "key": KEY}]
        added, skipped = bulk.import_items(self.vault, items, source="文件夹")
        self.assertEqual(len(added), 1)
        self.assertEqual(skipped, 1)
        entry = self.vault.by_kind("account")[0]
        self.assertEqual(entry["source"], "文件夹")

    def test_export_all_writes_folders_and_manifest(self):
        self.vault.add(name="同名", key=key(1))
        self.vault.add(name="同名", key=key(2))
        target = os.path.join(tempfile.mkdtemp(), "out.zip")
        count = bulk.export_all(self.vault, target, "东京放课后")
        self.assertEqual(count, 2)
        with zipfile.ZipFile(target) as zf:
            names = zf.namelist()
            self.assertIn("同名/AuthKey.txt", names)
            self.assertIn("同名 (2)/AuthKey.txt", names)
            manifest = zf.read("manifest.txt").decode("utf-8")
        self.assertIn("东京放课后", manifest)
        self.assertEqual(len(manifest.strip().splitlines()), 4)  # 标题 + 表头 + 两行

    def test_export_refuses_empty_section(self):
        target = os.path.join(tempfile.mkdtemp(), "empty.zip")
        count = bulk.export_all(self.vault, target, "东京放课后", kind="backup")
        self.assertEqual(count, 0)

    def test_safe_folder_strips_illegal_characters(self):
        self.assertEqual(bulk.safe_folder('a/b:c*?"<>|d'), "a_b_c______d")
        self.assertEqual(bulk.safe_folder("   "), "account")
        self.assertEqual(bulk.safe_folder("  ..name.. "), "name")

    def test_prune_keeps_recent_ten(self):
        for n in range(12):
            self.vault.add(name="备份 %d" % n, key=key(n), kind="backup")
        removed = bulk.prune_backups(self.vault, "10")
        self.assertEqual(len(removed), 2)
        self.assertEqual(len(self.vault.by_kind("backup")), 10)

    def test_prune_all_keeps_everything(self):
        for n in range(3):
            self.vault.add(name="备份 %d" % n, key=key(n), kind="backup")
        self.assertEqual(bulk.prune_backups(self.vault, "all"), [])
        self.assertEqual(len(self.vault.by_kind("backup")), 3)

    def test_prune_by_age_keeps_unknown_stamps(self):
        entry, _ = self.vault.add(name="旧备份", key=key(1), kind="backup")
        self.vault.update(entry["id"], name="旧备份")
        stored = self.vault.get(entry["id"])
        stored["created_at"] = "2000-01-01 00:00:00"
        self.assertEqual(bulk.prune_backups(self.vault, "30d"), [entry["id"]])

    def test_import_history_records_and_forgets(self):
        self.assertEqual(bulk.import_history(self.settings, "housamo"), [])
        entry, _ = self.vault.add(name="历史账号", key=key(3))
        bulk.record_import(self.settings, "housamo", entry, backup_id="b1")
        items = bulk.import_history(self.settings, "housamo")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["entry_id"], entry["id"])
        self.assertEqual(items[0]["backup_id"], "b1")
        self.assertTrue(items[0]["at"])
        self.assertEqual(bulk.last_import(self.settings, "housamo")["name"], "历史账号")
        bulk.forget_import(self.settings, "housamo")
        self.assertIsNone(bulk.last_import(self.settings, "housamo"))

    def test_import_history_is_per_game(self):
        entry, _ = self.vault.add(name="x", key=key(4))
        bulk.record_import(self.settings, "housamo", entry)
        self.assertEqual(bulk.import_history(self.settings, "liveahero"), [])


if __name__ == "__main__":
    unittest.main()
