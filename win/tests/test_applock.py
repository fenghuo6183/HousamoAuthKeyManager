# -*- coding: utf-8 -*-
import os
import tempfile
import unittest

from app import applock, config


class AppLockTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="hak-lock-")
        self.settings = config.Settings(os.path.join(self.dir, "settings.json"))

    def test_pin_shape(self):
        for pin in ("1234", "123456"):
            self.assertTrue(applock.valid_pin(pin))
        for pin in ("", "123", "1234567", "12a4", None):
            self.assertFalse(applock.valid_pin(pin))
        # surrounding spaces are trimmed on the way in and on the way out
        self.assertTrue(applock.valid_pin(" 1234 "))

    def test_set_and_check(self):
        self.assertFalse(applock.is_enabled(self.settings))
        applock.set_pin(self.settings, "2468")
        self.assertTrue(applock.is_enabled(self.settings))
        self.assertTrue(applock.check_pin(self.settings, "2468"))
        self.assertTrue(applock.check_pin(self.settings, " 2468 "))
        self.assertFalse(applock.check_pin(self.settings, "2469"))
        self.assertFalse(applock.check_pin(self.settings, ""))

    def test_rejects_bad_pin(self):
        with self.assertRaises(ValueError):
            applock.set_pin(self.settings, "12")
        self.assertFalse(applock.is_enabled(self.settings))

    def test_salt_is_random(self):
        applock.set_pin(self.settings, "1111")
        first = dict(self.settings.get("app_lock"))
        applock.set_pin(self.settings, "1111")
        second = dict(self.settings.get("app_lock"))
        self.assertNotEqual(first["salt"], second["salt"])
        self.assertNotEqual(first["hash"], second["hash"])
        self.assertNotIn("1111", str(second))

    def test_persists_across_reload(self):
        applock.set_pin(self.settings, "1357")
        again = config.Settings(os.path.join(self.dir, "settings.json"))
        self.assertTrue(applock.is_enabled(again))
        self.assertTrue(applock.check_pin(again, "1357"))

    def test_clear_pin(self):
        applock.set_pin(self.settings, "4321")
        applock.clear_pin(self.settings)
        self.assertFalse(applock.is_enabled(self.settings))
        # a cleared lock lets everything through, like a fresh install
        self.assertTrue(applock.check_pin(self.settings, "0000"))

    def test_corrupt_record_fails_closed(self):
        self.settings.set("app_lock", {"salt": "!!!", "hash": "!!!"})
        self.assertTrue(applock.is_enabled(self.settings))
        self.assertFalse(applock.check_pin(self.settings, "1234"))


if __name__ == "__main__":
    unittest.main()
