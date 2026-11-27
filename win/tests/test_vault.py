import base64
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["APPDATA"] = tempfile.mkdtemp(prefix="hak-test-")

from app import dpapi
from app import vault

KEY = b"housamo-test-key-0123456789-abcdef"


class VaultFilesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="vault-")
        self.path = os.path.join(self.tmp, "vault.housamo.dat")

    def test_path_per_game(self):
        self.assertTrue(vault.default_vault_path("housamo").endswith("vault.housamo.dat"))
        self.assertTrue(vault.default_vault_path("liveahero").endswith("vault.liveahero.dat"))

    def test_kind_defaults_to_account(self):
        v = vault.Vault(self.path, game_id="housamo")
        entry, created = v.add(name="a", key=KEY)
        self.assertTrue(created)
        self.assertEqual(entry["kind"], "account")
        self.assertEqual(entry["game"], "housamo")
        self.assertEqual(v.by_kind("backup"), [])
        self.assertEqual(len(v.by_kind("account")), 1)

    def test_backup_section(self):
        v = vault.Vault(self.path, game_id="housamo")
        v.add(name="b1", key=KEY, kind="backup")
        self.assertEqual(len(v.by_kind("backup")), 1)
        self.assertEqual(len(v.by_kind("account")), 0)

    def test_same_key_allowed_in_other_game_file(self):
        a = vault.Vault(os.path.join(self.tmp, "vault.housamo.dat"), game_id="housamo")
        b = vault.Vault(os.path.join(self.tmp, "vault.liveahero.dat"), game_id="liveahero")
        a.add(name="a", key=KEY)
        _, created = b.add(name="b", key=KEY)
        self.assertTrue(created)

    def test_legacy_entries_get_kind(self):
        entry = {"id": "x", "name": "old", "note": "",
                 "key_b64": base64.b64encode(KEY).decode(),
                 "fingerprint": "f", "sha256": "0"}
        payload = {"version": 1, "entries": [entry]}
        with open(self.path, "wb") as fh:
            fh.write(dpapi.protect(json.dumps(payload).encode("utf-8")))
        v = vault.Vault(self.path, game_id="housamo")
        self.assertEqual(v.entries[0]["kind"], "account")
        self.assertEqual(v.entries[0]["game"], "housamo")

    def test_hak_v2_roundtrip(self):
        src = vault.Vault(self.path, game_id="housamo")
        entry, _ = src.add(name="travel", key=KEY)
        hak = os.path.join(self.tmp, "travel.hak")
        src.export_hak(entry["id"], hak)
        with open(hak, encoding="utf-8") as fh:
            payload = json.load(fh)
        self.assertEqual(payload["version"], 2)
        self.assertEqual(payload["game"], "housamo")

        dst = vault.Vault(os.path.join(self.tmp, "v2.dat"), game_id="housamo")
        _, created = dst.import_hak(hak)
        self.assertTrue(created)

    def test_hak_wrong_game_refused(self):
        src = vault.Vault(self.path, game_id="housamo")
        entry, _ = src.add(name="travel", key=KEY)
        hak = os.path.join(self.tmp, "travel.hak")
        src.export_hak(entry["id"], hak)
        other = vault.Vault(os.path.join(self.tmp, "la.dat"), game_id="liveahero")
        with self.assertRaises(ValueError):
            other.import_hak(hak)

    def test_legacy_hak_without_game_imports(self):
        hak = os.path.join(self.tmp, "old.hak")
        with open(hak, "w", encoding="utf-8") as fh:
            json.dump({"format": "housamo-authkey-backup", "version": 1,
                       "name": "old", "key_b64": base64.b64encode(KEY).decode()}, fh)
        v = vault.Vault(os.path.join(self.tmp, "la.dat"), game_id="liveahero")
        _, created = v.import_hak(hak)
        self.assertTrue(created)


class ReplaceKeyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="vault-replace-")
        self.v = vault.Vault(os.path.join(self.tmp, "vault.housamo.dat"), game_id="housamo")

    def test_replace_keeps_entry_and_backs_up_old_key(self):
        entry, _ = self.v.add(name="主号", key=KEY)
        new_key = b"housamo-test-key-new-0123456789"
        updated, backup = self.v.replace_key(entry["id"], new_key)
        self.assertEqual(updated["id"], entry["id"])
        self.assertEqual(updated["name"], "主号")
        self.assertEqual(self.v.key_of(updated), new_key)
        self.assertIsNotNone(backup)
        self.assertEqual(backup["kind"], "backup")
        self.assertEqual(self.v.key_of(backup), KEY)
        self.assertEqual(self.v.find_same(KEY)["id"], backup["id"])
        self.assertEqual(len(self.v.by_kind("account")), 1)

    def test_replace_with_same_key_is_noop(self):
        entry, _ = self.v.add(name="a", key=KEY)
        updated, backup = self.v.replace_key(entry["id"], KEY)
        self.assertIsNone(backup)
        self.assertEqual(self.v.key_of(updated), KEY)
        self.assertEqual(len(self.v.by_kind("backup")), 0)

    def test_read_hak_does_not_add(self):
        entry, _ = self.v.add(name="a", key=KEY)
        path = os.path.join(self.tmp, "a.hak")
        self.v.export_hak(entry["id"], path)
        payload, key = self.v.read_hak(path)
        self.assertEqual(key, KEY)
        self.assertEqual(len(self.v.entries), 1)
        again, created = self.v.add_hak_payload(payload, key)
        self.assertEqual(again["id"], entry["id"])
        self.assertFalse(created)


class MigrateTest(unittest.TestCase):
    def test_migrates_legacy_vault(self):
        from app import config
        folder = config.app_dir()
        legacy = os.path.join(folder, "vault.dat")
        target = os.path.join(folder, "vault.housamo.dat")
        for path in (legacy, target):
            if os.path.exists(path):
                os.remove(path)
        with open(legacy, "wb") as fh:
            fh.write(b"old-bytes")
        self.assertTrue(vault.migrate_legacy_vault())
        self.assertFalse(os.path.exists(legacy))
        self.assertTrue(os.path.exists(target))
        self.assertFalse(vault.migrate_legacy_vault())


if __name__ == "__main__":
    unittest.main()
