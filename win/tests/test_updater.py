# -*- coding: utf-8 -*-
import hashlib
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-upd-")

from app import updater


class VersionTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(updater.parse_version("v1.2.10"), (1, 2, 10))
        self.assertEqual(updater.parse_version("1.2.0-beta"), (1, 2, 0))

    def test_newer(self):
        self.assertTrue(updater.is_newer("v1.2.0", "1.1.1"))
        self.assertFalse(updater.is_newer("v1.1.1", "1.1.1"))
        self.assertFalse(updater.is_newer("v1.0.9", "1.1.1"))

    def test_pick_asset_prefers_named_zip(self):
        release = {"assets": [
            {"name": "src.tar.gz", "browser_download_url": "https://x/src"},
            {"name": updater.ASSET_NAME, "browser_download_url": "https://x/z",
             "digest": "sha256:abc"}]}
        asset = updater.pick_asset(release)
        self.assertEqual(asset["url"], "https://x/z")

    def test_pick_asset_falls_back_to_any_zip(self):
        release = {"assets": [{"name": "foo.zip", "browser_download_url": "https://x/f"}]}
        self.assertEqual(updater.pick_asset(release)["name"], "foo.zip")

    def test_pick_asset_none(self):
        self.assertIsNone(updater.pick_asset({"assets": []}))

    def test_parse_desktop_tag(self):
        # The desktop line carries a "-win" suffix; 1.1 must still win over it.
        self.assertEqual(updater.parse_version("v1.0-win"), (1, 0))
        self.assertTrue(updater.is_newer("v1.1", "1.0-win"))
        self.assertFalse(updater.is_newer("v1.0-win", "1.0-win"))

    def test_select_release_skips_android_only(self):
        releases = [
            {"tag_name": "v1.2", "assets": [{"name": "HousamoAuthKeyManager-1.2.apk"}]},
            {"tag_name": "v1.0-win", "assets": [{"name": updater.ASSET_NAME}]},
            {"tag_name": "v0.9-win", "assets": [{"name": updater.ASSET_NAME}]},
        ]
        self.assertEqual(updater.select_release(releases)["tag_name"], "v1.0-win")

    def test_select_release_skips_drafts(self):
        releases = [
            {"tag_name": "v1.1", "draft": True, "assets": [{"name": updater.ASSET_NAME}]},
            {"tag_name": "v1.0-win", "assets": [{"name": updater.ASSET_NAME}]},
        ]
        self.assertEqual(updater.select_release(releases)["tag_name"], "v1.0-win")

    def test_select_release_empty(self):
        self.assertEqual(updater.select_release([]), {})
        self.assertEqual(updater.select_release([{"assets": [{"name": "a.apk"}]}]), {})


class ApplyTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="upd-")
        self.install = os.path.join(self.root, "install")
        os.makedirs(self.install)
        with open(os.path.join(self.install, "AuthKeyManager.exe"), "wb") as fh:
            fh.write(b"old")
        with open(os.path.join(self.install, "keep.txt"), "wb") as fh:
            fh.write(b"keep")

    def _zip(self, entries):
        path = os.path.join(self.root, "update.zip")
        with zipfile.ZipFile(path, "w") as zf:
            for name, data in entries.items():
                zf.writestr(name, data)
        return path

    def test_replace_and_clean(self):
        path = self._zip({"AuthKeyManager.exe": b"new", "sub/a.txt": "中文"})
        ok = updater.apply_update(path, self.install, 0, log=lambda *_: None)
        self.assertTrue(ok)
        with open(os.path.join(self.install, "AuthKeyManager.exe"), "rb") as fh:
            self.assertEqual(fh.read(), b"new")
        self.assertTrue(os.path.exists(os.path.join(self.install, "sub", "a.txt")))
        self.assertTrue(os.path.exists(os.path.join(self.install, "keep.txt")))
        self.assertEqual(updater.read_state()["stage"], "done")

    def test_strip_single_top_folder(self):
        path = self._zip({"AuthKeyManager/AuthKeyManager.exe": b"new"})
        self.assertTrue(updater.apply_update(path, self.install, 0, log=lambda *_: None))
        with open(os.path.join(self.install, "AuthKeyManager.exe"), "rb") as fh:
            self.assertEqual(fh.read(), b"new")

    def test_corrupt_zip_fails_and_records(self):
        bad = os.path.join(self.root, "bad.zip")
        with open(bad, "wb") as fh:
            fh.write(b"not a zip")
        self.assertFalse(updater.apply_update(bad, self.install, 0, log=lambda *_: None))
        self.assertEqual(updater.read_state()["stage"], "failed")

    def test_traversal_refused(self):
        path = self._zip({"../evil.txt": b"x"})
        self.assertFalse(updater.apply_update(path, self.install, 0, log=lambda *_: None))
        self.assertFalse(os.path.exists(os.path.join(self.root, "evil.txt")))

    def test_dir_writable(self):
        self.assertTrue(updater.dir_writable(self.install))

    def test_download_verifies_sha256(self):
        src = self._zip({"AuthKeyManager.exe": b"new"})
        with open(src, "rb") as fh:
            digest = "sha256:" + hashlib.sha256(fh.read()).hexdigest()
        url = "file:///" + src.replace("\\", "/")
        out = updater.download(url, digest, log=lambda *_: None)
        self.assertTrue(os.path.exists(out))
        self.assertGreater(os.path.getsize(out), 0)


if __name__ == "__main__":
    unittest.main()
