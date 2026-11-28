import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk

from app import adb, theme
from app.ui import App

EMU = "127.0.0.1:16384"


class FakeAdb:
    def __init__(self, devices):
        self.devices_now = list(devices)
        self.calls = 0

    def devices(self):
        self.calls += 1
        return list(self.devices_now)

    def su_available(self, serial):
        return True


def make_device(serial=EMU, model="MuMu-12", state="device"):
    dev = adb.Device(serial=serial, state=state, model=model)
    dev.root = "\u5426"
    return dev


class PollTest(unittest.TestCase):
    def setUp(self):
        os.environ["HOUSAMO_DATA_DIR"] = tempfile.mkdtemp(prefix="hak-poll-")
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

    def _pump(self, seconds=2.0, until=None):
        end = time.time() + seconds
        while time.time() < end:
            self.root.update()
            if until is not None and until():
                return True
            time.sleep(0.01)
        return until is None or bool(until())

    def test_poll_job_is_scheduled_without_hammering(self):
        self.assertIsNotNone(getattr(self.app, "_poll_job", None))
        self.assertGreaterEqual(self.app.POLL_MS, 3000)
        self.assertLessEqual(self.app.POLL_MS, 30000)

    def test_quiet_refresh_keeps_root_and_game_state(self):
        dev = make_device()
        self.app._devices_done([dev])
        dev.game_installed = True

        again = self.app._devices_worker(quiet=True)

        self.assertEqual(again[0].serial, EMU)
        self.assertEqual(again[0].root, "\u5426")
        self.assertIs(again[0].game_installed, True)

    def test_poll_marks_device_offline(self):
        dev = make_device()
        self.app.adb = FakeAdb([dev])
        self.app._poll_tick()
        self.assertTrue(self._pump(3.0, lambda: bool(self.app.devices)))
        self.assertTrue(self.app.devices[0].online)

        self.app.adb.devices_now = [make_device(state="offline")]
        self.app._poll_tick()
        self.assertTrue(self._pump(3.0, lambda: not self.app.devices[0].online))

        values = list(self.app.device_list.combo.cget("values"))
        self.assertTrue(any("\u79bb\u7ebf" in v for v in values), values)
        self.assertIn("\u79bb\u7ebf", self.app.dev_detail.cget("text"))

    def test_quiet_poll_does_not_log_every_time(self):
        self.app.adb = FakeAdb([make_device()])
        self.app._poll_tick()
        self.assertTrue(self._pump(3.0, lambda: bool(self.app.devices)))
        self.root.update()

        logged = []
        original = self.app.log
        self.app.log = lambda tag, msg: logged.append((tag, msg))
        try:
            self.app._poll_tick()
            self.assertTrue(self._pump(2.0))
        finally:
            self.app.log = original
        self.assertEqual(logged, [])


if __name__ == "__main__":
    unittest.main()
