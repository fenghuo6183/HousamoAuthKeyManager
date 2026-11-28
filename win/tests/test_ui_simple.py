import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk
import tkinter.ttk as ttk

from app import adb, theme
from app.ui import App

PHONE = ("R58M123ABC", "Pixel 7")
EMU = ("127.0.0.1:16384", "MuMu-12")


def make_device(serial, model="", state="device", product=""):
    dev = adb.Device(serial=serial, state=state, model=model, product=product)
    dev.root = "\u5426"
    return dev


class SimpleTasksPageTest(unittest.TestCase):
    """The task page is one plain card with a device dropdown (MAA style)."""

    def setUp(self):
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-simple-")
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

    def _load(self, *devices):
        self.app._devices_done(list(devices))
        self.root.update()

    def test_task_page_is_one_action_card_plus_the_recent_list(self):
        specs = self.app.pages["tasks"]
        self.assertEqual(len(specs), 2)
        self.assertIsNotNone(specs[0][1], "action card keeps its own height")
        self.assertIsNone(specs[1][1], "recent imports fill the rest")

    def test_device_selector_is_a_readonly_dropdown(self):
        self.assertIsInstance(self.app.device_list.combo, ttk.Combobox)
        self.assertEqual(str(self.app.device_list.combo.cget("state")), "readonly")

    def test_dropdown_lists_every_device(self):
        self._load(make_device(*PHONE), make_device(*EMU))
        values = list(self.app.device_list.combo.cget("values"))
        self.assertEqual(len(values), 2)
        self.assertTrue(any("MuMu-12" in v for v in values))

    def test_choosing_from_dropdown_switches_the_active_device(self):
        self._load(make_device(*PHONE), make_device(*EMU))
        self.app.device_list.combo.current(1)
        self.app.device_list.combo.event_generate("<<ComboboxSelected>>")
        self.root.update()
        self.assertEqual(self.app.selected_device().serial, EMU[0])

    def test_offline_device_is_marked_in_the_detail_line(self):
        self._load(make_device(EMU[0], EMU[1], state="offline"), make_device(*PHONE))
        self.app.select_device(EMU[0], persist=False, refresh_reconcile=False)
        self.root.update()
        self.assertIn("\u79bb\u7ebf", self.app.dev_detail.cget("text"))

    def test_refresh_button_rescans(self):
        wired = getattr(self.app.btn_refresh_device.command, "__func__", None)
        self.assertIs(wired, App.scan_emulators)
        self.assertEqual(self.app.btn_refresh_device.text, "刷新")


class ConnectProfileTest(unittest.TestCase):
    """设置 → 连接 offers presets that fill the address, like MAA."""

    def setUp(self):
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-prof-")
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

    def _pick(self, key):
        combo = self.app.connect_profile
        values = list(combo.cget("values"))
        index = next(i for i, v in enumerate(values) if key in v)
        combo.current(index)
        combo.event_generate("<<ComboboxSelected>>")
        self.root.update()

    def test_preset_fills_the_address(self):
        self._pick("MuMu")
        self.assertEqual(self.app.addr_var.get(), "127.0.0.1:16384")

    def test_another_preset_fills_its_own_port(self):
        self._pick("夜神")
        self.assertEqual(self.app.addr_var.get(), "127.0.0.1:62001")

    def test_profile_choice_is_remembered(self):
        self._pick("雷电")
        self.assertEqual(self.app.settings.get("connect_profile"), "ld")


if __name__ == "__main__":
    unittest.main()
