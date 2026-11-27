# -*- coding: utf-8 -*-
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-updui-")
os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk

from app import theme, updater
from app.ui import App


class UpdateCardTest(unittest.TestCase):
    def setUp(self):
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-updui-")
        theme.set_ui_scale(1.0)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root)
        self.root.update()

    def tearDown(self):
        self.root.destroy()

    def test_update_card_exists(self):
        self.assertIsNotNone(self.app.btn_check_update)
        self.assertIn(theme.APP_VERSION, self.app.update_version_label.cget("text"))

    def test_check_update_shows_new_version(self):
        release = {"tag_name": "v9.9.9", "html_url": "https://example/r",
                   "assets": [{"name": updater.ASSET_NAME,
                               "browser_download_url": "https://example/z"}]}
        with mock.patch.object(updater, "fetch_latest", return_value=release):
            self.app.check_update(manual=False)
            for _ in range(100):
                self.root.update()
                if self.app.update_asset is not None:
                    break
                time.sleep(0.02)
        self.assertIsNotNone(self.app.update_asset)
        self.assertEqual(self.app.btn_install_update.winfo_manager(), "pack")

    def test_apply_update_state_banner(self):
        updater.write_state(stage="failed", error="磁盘满了")
        self.app._apply_update_state()
        self.root.update()
        self.assertIn("磁盘满了", self.app.update_status.cget("text"))


if __name__ == "__main__":
    unittest.main()
