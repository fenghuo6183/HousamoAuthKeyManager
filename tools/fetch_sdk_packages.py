# -*- coding: utf-8 -*-
"""Fallback SDK fetch (sdkmanager needs network access Java sometimes lacks)."""
import os, sys, zipfile, shutil, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SDK = os.path.join(ROOT, ".tools", "android-sdk")
DL = os.path.join(ROOT, ".tools", "dl")

TARGETS = [
    ("platform-34-ext7_r03.zip", os.path.join(SDK, "platforms", "android-34")),
    ("build-tools_r34-windows.zip", os.path.join(SDK, "build-tools", "34.0.0")),
]

def log(*a): print(*a, flush=True)

def fetch(name):
    os.makedirs(DL, exist_ok=True)
    dst = os.path.join(DL, name)
    if os.path.exists(dst) and os.path.getsize(dst) > 100000:
        return dst
    url = "https://dl.google.com/android/repository/" + name
    log("[dl]", url)
    with urllib.request.urlopen(url, timeout=60) as r, open(dst + ".part", "wb") as f:
        total = int(r.headers.get("Content-Length") or 0); got = 0; last = 0
        while True:
            chunk = r.read(262144)
            if not chunk: break
            f.write(chunk); got += len(chunk)
            if got - last > 8 * 1048576:
                last = got; log("   %.1fMB/%dMB" % (got / 1048576, total // 1048576))
    os.replace(dst + ".part", dst)
    return dst

for name, dest in TARGETS:
    if os.path.isdir(dest) and os.listdir(dest):
        log("[skip]", dest); continue
    zp = fetch(name)
    tmp = os.path.join(ROOT, ".tools", "_unzip_" + name)
    if os.path.isdir(tmp): shutil.rmtree(tmp)
    os.makedirs(tmp)
    log("[unzip]", name)
    zipfile.ZipFile(zp).extractall(tmp)
    entries = os.listdir(tmp)
    src = os.path.join(tmp, entries[0]) if len(entries) == 1 and os.path.isdir(os.path.join(tmp, entries[0])) else tmp
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.isdir(dest): shutil.rmtree(dest)
    shutil.move(src, dest)
    shutil.rmtree(tmp, ignore_errors=True)
    log("[ok]", dest, sorted(os.listdir(dest))[:6])

log("aapt2:", os.path.join(SDK, "build-tools", "34.0.0", "aapt2.exe"))
log("d8:", os.path.join(SDK, "build-tools", "34.0.0", "d8.bat"))
log("android.jar:", os.path.join(SDK, "platforms", "android-34", "android.jar"))
