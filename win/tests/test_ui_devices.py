import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk

from app import adb, config, theme
from app.ui import App


def make_device(serial, model="", state="device", product=""):
    dev = adb.Device(serial=serial, state=state, model=model, product=product)
    dev.root = "\u5426"
    return dev


PHONE = ("R58M123ABC", "Pixel 7")
EMU = ("127.0.0.1:16384", "MuMu-12")


class DeviceSelectTest(unittest.TestCase):
    def setUp(self):
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-uid-")
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

    def test_selecting_emulator_persists_preference(self):
        self._load(make_device(*PHONE), make_device(*EMU))
        self.app.select_device(EMU[0])

        self.assertEqual(self.app.selected_device().serial, EMU[0])
        self.assertEqual(self.app.settings.get("preferred_serial"), EMU[0])
        saved = config.Settings()
        self.assertEqual(saved.get("preferred_serial"), EMU[0])

    def test_refresh_keeps_the_device_the_user_picked(self):
        self._load(make_device(*PHONE), make_device(*EMU))
        self.app.select_device(EMU[0])
        self._load(make_device(*PHONE), make_device(*EMU))

        self.assertEqual(self.app.selected_device().serial, EMU[0])

    def test_preferred_device_is_selected_on_startup(self):
        self.app.settings.set("preferred_serial", EMU[0])
        self._load(make_device(*PHONE), make_device(*EMU))

        self.assertEqual(self.app.selected_device().serial, EMU[0])

    def test_offline_preferred_device_falls_back_to_an_online_one(self):
        self.app.settings.set("preferred_serial", EMU[0])
        self._load(make_device(*PHONE),
                   make_device(EMU[0], EMU[1], state="offline"))

        self.assertEqual(self.app.selected_device().serial, PHONE[0])

    def test_only_emulators_hides_usb_phone(self):
        self.app.settings.set("only_emulators", True)
        self._load(make_device(*PHONE), make_device(*EMU))

        self.assertIn(EMU[0], self.app.device_list.serials())
        self.assertNotIn(PHONE[0], self.app.device_list.serials())

    def test_extract_button_names_the_selected_device(self):
        self._load(make_device(*PHONE), make_device(*EMU))
        self.app.select_device(EMU[0])

        self.assertIn(EMU[1], self.app.btn_extract.text)

    def test_connect_button_normalizes_short_address(self):
        self.assertEqual(adb.normalize_address("127.0.0.1"), "127.0.0.1:5555")
        self.assertEqual(adb.normalize_address(" 127.0.0.1:7555 "), "127.0.0.1:7555")
        self.assertEqual(adb.normalize_address("16384"), "127.0.0.1:16384")
        self.assertEqual(adb.normalize_address(""), "")

    def test_emulator_serial_detection(self):
        self.assertTrue(adb.is_emulator_serial("127.0.0.1:16384"))
        self.assertTrue(adb.is_emulator_serial("emulator-5554"))
        self.assertFalse(adb.is_emulator_serial("R58M123ABC"))


if __name__ == "__main__":
    unittest.main()


class DevicePickerLayoutTest(unittest.TestCase):
    """The device picker is a dropdown, so it has a fixed height."""

    def setUp(self):
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-uid-")
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

    def test_dropdown_lists_both_devices(self):
        self.app._devices_done([make_device(*PHONE), make_device(*EMU)])
        self.root.update()
        values = list(self.app.device_list.combo.cget("values"))
        self.assertEqual(len(values), 2)

    def test_long_device_name_widens_the_extract_button(self):
        wide = make_device("127.0.0.1:7555", "An Extremely Long Emulator Alias")
        self.app._devices_done([wide])
        self.app.select_device(wide.serial, persist=False, refresh_reconcile=False)
        self.root.update()

        narrow = self.app.btn_extract._width
        self.app.select_device("nothing-here", persist=False, refresh_reconcile=False)
        self.root.update()
        self.assertGreaterEqual(narrow, self.app.btn_extract._width)
