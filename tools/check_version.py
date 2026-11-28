# -*- coding: utf-8 -*-
"""Check that the Windows and Android version numbers agree.

win/app/theme.py APP_VERSION is the single source of truth; the three Android
places must carry the very same string.  Run it before building a release:

    python tools/check_version.py
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with io.open(os.path.join(ROOT, rel), encoding="utf-8") as handle:
        return handle.read()


def find(pattern, text, what):
    match = re.search(pattern, text)
    if not match:
        raise SystemExit("cannot find " + what)
    return match.group(1)


def main():
    win = find(r'APP_VERSION\s*=\s*"([^"]+)"', read("win/app/theme.py"), "APP_VERSION")
    manifest = read("android/AndroidManifest.xml")
    build = read("android/build_apk.py")
    activity = read("android/src/com/housamo/authkey/MainActivity.java")
    name = find(r'android:versionName="([^"]+)"', manifest, "versionName")
    code = find(r'android:versionCode="([^"]+)"', manifest, "versionCode")
    bname = find(r'VERSION_NAME\s*=\s*"([^"]+)"', build, "VERSION_NAME")
    bcode = find(r'VERSION_CODE\s*=\s*"([^"]+)"', build, "VERSION_CODE")
    current = find(r'CURRENT_VER\s*=\s*"([^"]+)"', activity, "CURRENT_VER")

    rows = [("win/app/theme.py  APP_VERSION", win),
            ("AndroidManifest     versionName", name),
            ("build_apk.py        VERSION_NAME", bname),
            ("MainActivity.java   CURRENT_VER", current)]
    bad = []
    for label, value in rows:
        print(("  OK   " if value == win else "  BAD  ") + label + " = " + value)
        if value != win:
            bad.append(label)
    print("  versionCode: AndroidManifest=" + code + " build_apk=" + bcode)
    if code != bcode:
        bad.append("versionCode")
    if bad:
        print("")
        print("mismatch: " + ", ".join(bad) + " (all should be " + win + ")")
        return 1
    print("")
    print("all consistent: " + win + " (versionCode " + code + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
