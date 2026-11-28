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

    # -- 启动自动检查要主动弹更新框 ------------------------------------
    @staticmethod
    def _release(tag="v9.9.9"):
        return {"tag_name": tag, "html_url": "https://example/r",
                "assets": [{"name": updater.ASSET_NAME,
                            "browser_download_url": "https://example/z"}]}

    def _wait_for(self, predicate):
        for _ in range(150):
            self.root.update()
            if predicate():
                return True
            time.sleep(0.02)
        return False

    def test_startup_check_pops_update_dialog(self):
        with mock.patch.object(updater, "fetch_latest", return_value=self._release()):
            self.app._auto_update_check()
            self.assertTrue(self._wait_for(
                lambda: self.app._update_prompt_win is not None))
        win = self.app._update_prompt_win
        self.assertEqual(win.winfo_exists(), 1)
        self.assertEqual(self.app._prompted_update, "v9.9.9")
        # 同一次运行里同一个版本，再自动检查一次不再弹第二个框
        with mock.patch.object(updater, "fetch_latest", return_value=self._release()):
            self.app.check_update(manual=False)
            self.assertTrue(self._wait_for(
                lambda: self.app.update_asset is not None))
        self.assertIs(self.app._update_prompt_win, win)

    def test_later_then_manual_reopens(self):
        with mock.patch.object(updater, "fetch_latest", return_value=self._release()):
            self.app.check_update(manual=False)
            self.assertTrue(self._wait_for(
                lambda: self.app._update_prompt_win is not None))
        self.app._close_update_prompt()
        self.assertIsNone(self.app._update_prompt_win)
        # 点过「稍后再说」，这次运行里自动检查不再弹
        with mock.patch.object(updater, "fetch_latest", return_value=self._release()):
            self.app.check_update(manual=False)
            self.assertTrue(self._wait_for(
                lambda: self.app.update_asset is not None))
        self.assertIsNone(self.app._update_prompt_win)
        # 但手动点「检查更新」应该再弹一次
        with mock.patch.object(updater, "fetch_latest", return_value=self._release()):
            self.app.check_update(manual=True)
            self.assertTrue(self._wait_for(
                lambda: self.app._update_prompt_win is not None))


if __name__ == "__main__":
    unittest.main()
