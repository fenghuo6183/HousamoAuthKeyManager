import io
import os
import sys
import unittest
import urllib.error
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import lanshare

ROWS = [
    {"name": "主号", "note": "日常", "fingerprint": "ab12…9f3d (128)",
     "key": "housamo-key-aaaa", "created_at": "2026-11-20 21:04"},
    {"name": "小号", "note": "", "fingerprint": "7c44…1e02 (128)",
     "key": "housamo-key-bbbb", "created_at": "2026-11-22 10:31"},
]


class LanServerTest(unittest.TestCase):
    def setUp(self):
        self.server = lanshare.LanServer(lambda: list(ROWS), "东京放课后", port=8790)
        self.server.start()
        self.base = "http://127.0.0.1:%d" % self.server.port

    def tearDown(self):
        self.server.stop()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=5) as resp:
            return resp.status, resp.read()

    def test_code_is_four_digits(self):
        self.assertEqual(len(self.server.code), 4)
        self.assertTrue(self.server.code.isdigit())

    def test_wrong_code_is_forbidden(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/?k=0000")
        self.assertEqual(ctx.exception.code, 403)

    def test_lists_accounts(self):
        status, body = self.get("/?k=" + self.server.code)
        self.assertEqual(status, 200)
        text = body.decode("utf-8")
        self.assertIn("东京放课后", text)
        self.assertIn("主号", text)
        self.assertIn("/key?i=1", text)
        self.assertIn("/zip?k=", text)

    def test_serves_single_key(self):
        status, body = self.get("/key?i=0&k=" + self.server.code)
        self.assertEqual(status, 200)
        self.assertEqual(body, b"housamo-key-aaaa")

    def test_unknown_index_is_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/key?i=9&k=" + self.server.code)
        self.assertEqual(ctx.exception.code, 404)

    def test_zip_contains_folders_and_manifest(self):
        status, body = self.get("/zip?k=" + self.server.code)
        self.assertEqual(status, 200)
        with zipfile.ZipFile(io.BytesIO(body)) as zf:
            names = zf.namelist()
            self.assertIn("主号/AuthKey.txt", names)
            self.assertIn("manifest.txt", names)
            self.assertEqual(zf.read("主号/AuthKey.txt"), b"housamo-key-aaaa")

    def test_build_zip_dedupes_folder_names(self):
        data = lanshare.build_zip([dict(ROWS[0]), dict(ROWS[0])], "游戏")
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            self.assertIn("主号/AuthKey.txt", zf.namelist())
            self.assertIn("主号 (2)/AuthKey.txt", zf.namelist())

    def test_url_has_code(self):
        self.assertIn("/?k=" + self.server.code, self.server.url())

    def test_stop_is_idempotent(self):
        self.server.stop()
        self.server.stop()


if __name__ == "__main__":
    unittest.main()
