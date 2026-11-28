"""Persistent log file so a bad session can still be inspected later."""

from __future__ import annotations

import os
import time

from . import config

MAX_BYTES = 1_500_000
NAME = "app.log"


def log_dir():
    path = os.path.join(config.app_dir(), "logs")
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass
    return path


def log_path():
    return os.path.join(log_dir(), NAME)


def write(tag, message):
    """Append one line; silent on failure (logging must never break the app)."""
    try:
        path = log_path()
        if os.path.exists(path) and os.path.getsize(path) > MAX_BYTES:
            old = os.path.join(log_dir(), "app.1.log")
            try:
                if os.path.exists(old):
                    os.remove(old)
                os.replace(path, old)
            except Exception:
                pass
        line = "%s  [%s] %s\n" % (
            time.strftime("%Y-%m-%d %H:%M:%S"), tag, message)
        with open(path, "a", encoding="utf-8", errors="replace") as fh:
            fh.write(line)
        return True
    except Exception:
        return False


def tail(lines=400):
    try:
        with open(log_path(), "r", encoding="utf-8", errors="replace") as fh:
            return "".join(fh.readlines()[-lines:])
    except Exception:
        return ""
