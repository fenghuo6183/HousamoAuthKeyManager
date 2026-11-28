# -*- coding: utf-8 -*-
"""两端版本号必须一致：win/app/theme.py 是基准，安卓三处跟着它走。"""
import io
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def read(rel):
    return io.open(os.path.join(ROOT, rel), encoding="utf-8").read()


def grab(pattern, text, what):
    match = re.search(pattern, text)
    if not match:
        raise AssertionError("cannot find " + what)
    return match.group(1)


class VersionSyncTest(unittest.TestCase):
    def test_android_versions_match_windows(self):
        manifest_path = os.path.join(ROOT, "android", "AndroidManifest.xml")
        if not os.path.exists(manifest_path):
            self.skipTest("android sources not present")
        win = grab(r'APP_VERSION\s*=\s*"([^"]+)"', read(os.path.join("win", "app", "theme.py")), "APP_VERSION")
        manifest = read(os.path.join("android", "AndroidManifest.xml"))
        build = read(os.path.join("android", "build_apk.py"))
        activity = read(os.path.join("android", "src", "com", "housamo", "authkey", "MainActivity.java"))

        self.assertEqual(grab(r'android:versionName="([^"]+)"', manifest, "versionName"), win)
        self.assertEqual(grab(r'VERSION_NAME\s*=\s*"([^"]+)"', build, "VERSION_NAME"), win)
        self.assertEqual(grab(r'CURRENT_VER\s*=\s*"([^"]+)"', activity, "CURRENT_VER"), win)
        code = grab(r'android:versionCode="([^"]+)"', manifest, "versionCode")
        self.assertEqual(grab(r'VERSION_CODE\s*=\s*"([^"]+)"', build, "VERSION_CODE"), code)
        self.assertTrue(code.isdigit())


if __name__ == "__main__":
    unittest.main()
