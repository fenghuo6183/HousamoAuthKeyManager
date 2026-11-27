# -*- coding: utf-8 -*-
"""Download the Android build toolchain (JDK 17 + Android SDK cmdline-tools)."""
import os, sys, zipfile, shutil, subprocess, urllib.request, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, ".tools")
DL = os.path.join(TOOLS, "dl")
SDK = os.path.join(TOOLS, "android-sdk")
JDK_DIR = os.path.join(TOOLS, "jdk")

URLS = {
    "jdk": "https://mirrors.tuna.tsinghua.edu.cn/Adoptium/17/jdk/x64/windows/OpenJDK17U-jdk_x64_windows_hotspot_17.0.21.1_2.zip",
    "cmdline-tools": "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip",
    "platform-tools": "https://dl.google.com/android/repository/platform-tools-latest-windows.zip",
}

def log(*a):
    print(*a, flush=True)

def download(name, url):
    os.makedirs(DL, exist_ok=True)
    dst = os.path.join(DL, name + ".zip")
    if os.path.exists(dst) and os.path.getsize(dst) > 1000000:
        log("[skip] already downloaded", dst, os.path.getsize(dst))
        return dst
    log("[dl]", name, url)
    tmp = dst + ".part"
    with urllib.request.urlopen(url, timeout=60) as r, open(tmp, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        last = 0
        while True:
            chunk = r.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if got - last > 8 * 1024 * 1024:
                last = got
                pct = (got * 100 // total) if total else 0
                log("   %s %.1fMB/%sMB %d%%" % (name, got / 1048576, round(total / 1048576), pct))
    os.replace(tmp, dst)
    log("[ok]", name, os.path.getsize(dst))
    return dst

def unzip(zp, dest):
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(zp) as z:
        z.extractall(dest)

def main():
    os.makedirs(TOOLS, exist_ok=True)
    # JDK
    if not os.path.isdir(JDK_DIR):
        zp = download("jdk", URLS["jdk"])
        tmp = os.path.join(TOOLS, "_jdk_tmp")
        if os.path.isdir(tmp): shutil.rmtree(tmp)
        unzip(zp, tmp)
        inner = [d for d in os.listdir(tmp) if os.path.isdir(os.path.join(tmp, d))]
        os.replace(os.path.join(tmp, inner[0]), JDK_DIR)
        shutil.rmtree(tmp, ignore_errors=True)
        log("[ok] jdk ->", JDK_DIR)
    java = os.path.join(JDK_DIR, "bin", "java.exe")
    log("[jdk]", subprocess.run([java, "-version"], capture_output=True, text=True).stderr.strip()[:120])

    # platform-tools (adb)
    pt = os.path.join(SDK, "platform-tools")
    if not os.path.exists(os.path.join(pt, "adb.exe")):
        zp = download("platform-tools", URLS["platform-tools"])
        tmp = os.path.join(TOOLS, "_pt_tmp")
        if os.path.isdir(tmp): shutil.rmtree(tmp)
        unzip(zp, tmp)
        os.makedirs(SDK, exist_ok=True)
        if os.path.isdir(pt): shutil.rmtree(pt)
        shutil.move(os.path.join(tmp, "platform-tools"), pt)
        shutil.rmtree(tmp, ignore_errors=True)
        log("[ok] platform-tools ->", pt)

    # cmdline-tools
    ct = os.path.join(SDK, "cmdline-tools", "latest")
    if not os.path.exists(os.path.join(ct, "bin", "sdkmanager.bat")):
        zp = download("cmdline-tools", URLS["cmdline-tools"])
        tmp = os.path.join(TOOLS, "_ct_tmp")
        if os.path.isdir(tmp): shutil.rmtree(tmp)
        unzip(zp, tmp)
        os.makedirs(os.path.dirname(ct), exist_ok=True)
        if os.path.isdir(ct): shutil.rmtree(ct)
        shutil.move(os.path.join(tmp, "cmdline-tools"), ct)
        shutil.rmtree(tmp, ignore_errors=True)
        log("[ok] cmdline-tools ->", ct)

    # install sdk packages
    sdkmanager = os.path.join(ct, "bin", "sdkmanager.bat")
    env = dict(os.environ)
    env["JAVA_HOME"] = JDK_DIR
    env["PATH"] = os.path.join(JDK_DIR, "bin") + os.pathsep + env.get("PATH", "")
    pkgs = ["platform-tools", "platforms;android-34", "build-tools;34.0.0"]
    if not os.path.isdir(os.path.join(SDK, "build-tools", "34.0.0")):
        log("[sdk] installing", pkgs)
        p = subprocess.run(["cmd", "/c", sdkmanager, "--sdk_root=" + SDK] + pkgs,
                           input=("y\n" * 60), capture_output=True, text=True, env=env)
        log(p.stdout[-2000:]); log(p.stderr[-1500:])
    log("[done] SDK at", SDK)
    log("adb:", os.path.join(pt, "adb.exe"))
    log("android.jar:", os.path.join(SDK, "platforms", "android-34", "android.jar"))

if __name__ == "__main__":
    main()
