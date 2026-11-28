# -*- coding: utf-8 -*-
"""前三次从游戏提取 key 的强提醒（必须读满 3 秒）回归测试。"""

import os
import sys
import tempfile
import types
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("HOUSAMO_NO_ADB", "1")

import tkinter as tk

from app import dialogs, theme
from app import ui as ui_mod
from app.config import Settings
from app.ui import App

KEY = b"export-tip-key-0123456789-cccc"


class ExportReminderDialogTest(unittest.TestCase):
    def setUp(self):
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-uitip-")
        theme.set_ui_scale(1.0)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root)
        self.root.update()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_countdown_locks_button_until_it_ends(self):
        dlg = dialogs.InfoDialog(self.app, title="提醒", lines=["正文"], seconds=3)
        self.assertEqual(dlg.btn.text, "请先读完（3 秒）")
        self.assertFalse(dlg.btn._enabled)

        dlg._tick(2)
        self.assertEqual(dlg.btn.text, "请先读完（2 秒）")
        self.assertFalse(dlg.btn._enabled)

        dlg._tick(0)
        self.assertEqual(dlg.btn.text, "我知道了")
        self.assertTrue(dlg.btn._enabled)
        dlg.close()

    def test_zero_seconds_is_confirmable_right_away(self):
        dlg = dialogs.InfoDialog(self.app, title="提醒", lines=["正文"], seconds=0,
                                 confirm="我知道了，去保存")
        self.assertEqual(dlg.btn.text, "我知道了，去保存")
        self.assertTrue(dlg.btn._enabled)

        dlg.ok()
        self.assertTrue(dlg.result)
        self.assertFalse(dlg.window.winfo_exists())

    def test_export_reminder_names_both_places(self):
        captured = {}

        class FakeDialog:
            def __init__(self, app, **kwargs):
                captured.update(kwargs)
                self.result = True
                self.window = tk.Toplevel(app.root)
                self.window.withdraw()
                # show_export_reminder 会 wait_window，这里让它立刻返回
                self.window.after(1, self.window.destroy)

            def close(self):
                self.window.destroy()

        with mock.patch.object(dialogs, "InfoDialog", FakeDialog):
            dialogs.show_export_reminder(self.app, game_label="东京放课后")
        joined = "".join(captured.get("lines") or [])
        self.assertIn("手机", joined)
        self.assertIn("电脑", joined)
        self.assertEqual(captured.get("seconds"), 3)


class ExportTipCounterTest(unittest.TestCase):
    def setUp(self):
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-uitip-")
        theme.set_ui_scale(1.0)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root)
        self.root.update()
        self.prompts = []

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def _extract_once(self):
        dev = types.SimpleNamespace(serial="emulator-5554")
        with mock.patch.object(self.app, "_require", return_value=True), \
                mock.patch.object(self.app, "selected_device", return_value=dev), \
                mock.patch.object(ui_mod.game, "extract", return_value=(KEY, "设备存储")), \
                mock.patch.object(dialogs, "show_export_reminder",
                                  side_effect=lambda app, **kw: self.prompts.append(1)), \
                mock.patch.object(dialogs, "ask_text", return_value=""), \
                mock.patch.object(self.app, "reveal_entry"), \
                mock.patch.object(self.app, "export_to_dir", return_value=None), \
                mock.patch.object(self.app, "_bg",
                                  side_effect=lambda worker, done: done(worker())):
            self.app.do_extract()

    def test_reminder_only_for_first_three_extractions(self):
        for _ in range(4):
            self._extract_once()

        self.assertEqual(len(self.prompts), 3)
        self.assertEqual(self.app.export_tip_shown(), 3)
        self.assertEqual(self.app.settings.get("export_tip_shown"), 3)

    def test_counter_survives_restart(self):
        self._extract_once()
        self.app.settings.save()
        self.assertEqual(Settings().get("export_tip_shown"), 1)


if __name__ == "__main__":
    unittest.main()
