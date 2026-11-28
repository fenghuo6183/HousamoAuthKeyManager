# -*- coding: utf-8 -*-
"""Thin, dependency-free ADB wrapper."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass

class AdbError(RuntimeError):
    pass

_NO_WINDOW = 0
if sys.platform.startswith("win"):
    _NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)


def _bundled_dirs():
    here = os.path.dirname(os.path.abspath(__file__))
    roots = [here, os.path.dirname(here), os.path.dirname(os.path.dirname(here))]
    base = getattr(sys, "_MEIPASS", None)
    if base:
        roots.insert(0, base)
    dirs = []
    for root in roots:
        dirs.append(os.path.join(root, "assets", "platform-tools"))
        dirs.append(os.path.join(root, "platform-tools"))
    return dirs


def find_adb():
    env = os.environ.get("HOUSAMO_ADB")
    if env and os.path.isfile(env):
        return env
    for d in _bundled_dirs():
        p = os.path.join(d, "adb.exe")
        if os.path.isfile(p):
            return p
    found = shutil.which("adb")
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA") or ""
    candidates = [
        os.path.join(local, "Android", "Sdk", "platform-tools", "adb.exe"),
        "C:/platform-tools/adb.exe",
        "C:/adb/adb.exe",
        "D:/platform-tools/adb.exe",
    ]
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None


@dataclass
class Device:
    serial: str
    state: str
    model: str = ""
    product: str = ""
    transport: str = ""
    root: str = "?"
    game_installed: object = None   # None = 还没检测，True/False = 已检测

    @property
    def short_label(self):
        """Name shown in buttons: "MuMu-12", "Pixel 7", "设备"."""
        name = (self.model or self.product or "").strip()
        if name:
            return name
        return "模拟器" if is_emulator_serial(self.serial) else "设备"

    @property
    def is_emulator(self):
        return is_emulator_serial(self.serial)

    @property
    def label(self):
        name = self.model or self.product or "未知设备"
        return "%s (%s)" % (name, self.serial)

    @property
    def online(self):
        return self.state == "device"


class Adb:
    def __init__(self, path=None):
        self.path = path or find_adb()
        self.version = ""
        if not self.path:
            raise AdbError("未找到 adb.exe。请把 platform-tools 放进程序目录的 assets/platform-tools/，或安装 Android SDK。")

    def run(self, args, timeout=25, binary=False, check=False):
        cmd = [self.path] + list(args)
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=_NO_WINDOW)
        except subprocess.TimeoutExpired:
            raise AdbError("adb 命令超时: " + " ".join(args))
        except OSError as exc:
            raise AdbError("无法启动 adb: %s" % exc)
        if binary:
            return proc.stdout, proc.returncode, proc.stderr
        out = proc.stdout.decode("utf-8", "replace")
        err = proc.stderr.decode("utf-8", "replace")
        if check and proc.returncode != 0:
            raise AdbError((err or out).strip() or ("adb 命令失败: " + " ".join(args)))
        return out, err, proc.returncode

    def ensure_server(self):
        out, err, _ = self.run(["version"], timeout=20)
        self.version = out.strip().splitlines()[0] if out.strip() else ""
        self.run(["start-server"], timeout=30)

    def devices(self):
        out, err, code = self.run(["devices", "-l"], timeout=20)
        if code != 0 and not out:
            raise AdbError(err.strip() or "adb devices failed")
        result = []
        for line in out.splitlines():
            line = line.strip()
            if not line or line.startswith("List of devices") or line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial, state = parts[0], parts[1]
            info = {}
            for token in parts[2:]:
                if ":" in token:
                    k, v = token.split(":", 1)
                    info[k] = v
            result.append(Device(serial=serial, state=state,
                                 model=info.get("model", "").replace("_", " "),
                                 product=info.get("product", ""),
                                 transport=info.get("transport_id", "")))
        return result

    def connect(self, host_port, timeout=8):
        out, err, code = self.run(["connect", host_port], timeout=timeout)
        text = (out + err).strip()
        low = text.lower()
        ok = "connected to" in low and "cannot" not in low and "failed" not in low
        return ok, text

    def shell(self, serial, command, timeout=20):
        out, err, code = self.run(["-s", serial, "shell", command], timeout=timeout)
        return out

    def shell_stdin(self, serial, command, data, timeout=30):
        """Run a shell command and feed `data` to its stdin (adb forwards stdin)."""
        cmd = [self.path, "-s", serial, "shell", command]
        try:
            proc = subprocess.run(cmd, input=data, capture_output=True, timeout=timeout,
                                  creationflags=_NO_WINDOW)
        except subprocess.TimeoutExpired:
            raise AdbError("adb 命令超时: " + command)
        except OSError as exc:
            raise AdbError("无法启动 adb: %s" % exc)
        out = proc.stdout.decode("utf-8", "replace")
        err = proc.stderr.decode("utf-8", "replace")
        return out, err, proc.returncode

    def shell_bytes(self, serial, command, timeout=20):
        out, _, _ = self.run(["-s", serial, "exec-out", command], timeout=timeout, binary=True)
        return out

    def su_available(self, serial):
        try:
            out, _, code = self.run(["-s", serial, "shell", "su -c id"], timeout=8)
            return code == 0 and "uid=0" in out
        except AdbError:
            return False

    def push(self, serial, local, remote, timeout=90):
        out, err, code = self.run(["-s", serial, "push", local, remote], timeout=timeout)
        if code != 0:
            raise AdbError(err.strip() or out.strip() or "adb push failed")

    def pull(self, serial, remote, local, timeout=90):
        out, err, code = self.run(["-s", serial, "pull", remote, local], timeout=timeout)
        if code != 0:
            raise AdbError(err.strip() or out.strip() or "adb pull failed")


def parse_android_version(adb, serial):
    try:
        return adb.shell(serial, "getprop ro.build.version.release", timeout=10).strip()
    except AdbError:
        return ""


def is_emulator_serial(serial):
    """True for network devices (127.0.0.1:16384) and AVD style serials."""
    text = (serial or "").strip()
    if not text:
        return False
    return text.startswith("emulator-") or ":" in text


def normalize_address(text, default_port=5555):
    """Turn what a user types into a usable adb connect address.

    "127.0.0.1", "127.0.0.1:16384", "16384" and "localhost:7555" all work.
    Empty input stays empty so callers can treat it as "nothing typed".
    """
    raw = (text or "").strip().replace(" ", "")
    if not raw:
        return ""
    if raw.isdigit():
        return "127.0.0.1:%d" % int(raw)
    if raw.count(":") == 1:
        host, _, port = raw.partition(":")
        if host and port.isdigit() and 0 < int(port) < 65536:
            return "%s:%d" % (host, int(port))
    raw = raw.rstrip(":")
    return "%s:%d" % (raw, default_port)
