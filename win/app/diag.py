"""One-click diagnostics bundle: logs + environment + settings (redacted)."""

from __future__ import annotations

import json
import os
import platform
import sys
import time
import zipfile

from . import config, logfile, theme


def _settings_dump():
    try:
        with open(config.settings_path(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception as exc:
        return "无法读取设置：%s" % exc
    if not isinstance(data, dict):
        return json.dumps(data, ensure_ascii=False, indent=2)
    for key in ("webhook_url",):
        value = data.get(key)
        if isinstance(value, str) and value:
            data[key] = "****" + value[-4:]
    return json.dumps(data, ensure_ascii=False, indent=2)


def system_text(extra=""):
    try:
        from PySide6 import __version__ as qt_version
    except Exception:
        qt_version = "?"
    lines = [
        "%s 诊断信息" % theme.APP_TITLE if hasattr(theme, "APP_TITLE") else "诊断信息",
        "时间      : %s" % time.strftime("%Y-%m-%d %H:%M:%S"),
        "版本      : %s" % getattr(theme, "APP_VERSION", "?"),
        "系统      : %s" % platform.platform(),
        "Python    : %s" % sys.version.replace("\n", " "),
        "Qt        : %s" % qt_version,
        "打包运行  : %s" % ("是" if getattr(sys, "frozen", False) else "否"),
        "程序路径  : %s" % (sys.executable or "?"),
        "数据目录  : %s" % config.app_dir(),
        "日志文件  : %s" % logfile.log_path(),
        "界面缩放  : %s" % getattr(theme, "UI_SCALE", "?"),
    ]
    if extra:
        lines += ["", extra]
    return "\n".join(lines)


def build_bundle(dest_path, extra=""):
    """Write a zip to dest_path; returns (ok, message)."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr("system.txt", system_text(extra))
            bundle.writestr("settings.json", _settings_dump())
            for name in (logfile.NAME, "app.1.log"):
                path = os.path.join(logfile.log_dir(), name)
                if os.path.exists(path):
                    bundle.write(path, "logs/%s" % name)
            bundle.writestr("README.txt",
                            "把整个 zip 发给开发者即可排查问题。\n"
                            "settings.json 里的 webhook 地址已打码。\n")
        return True, dest_path
    except Exception as exc:
        return False, str(exc)
