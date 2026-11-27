# -*- coding: utf-8 -*-
"""Windows DPAPI helpers (CryptProtectData / CryptUnprotectData)."""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt

MAGIC_DPAPI = b"HAK1"
MAGIC_PLAIN = b"HAK0"

IS_WINDOWS = __import__("sys").platform.startswith("win")


class _DATA_BLOB(ctypes.Structure):
    _fields_ = [("cbData", wt.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _blob(data):
    buf = ctypes.create_string_buffer(data, len(data))
    return _DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))


def _blob_bytes(blob):
    return ctypes.string_at(blob.pbData, blob.cbData)


def protect(data):
    if not IS_WINDOWS:
        return MAGIC_PLAIN + data
    in_blob = _blob(data)
    out_blob = _DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob), "HousamoAuthKeyManager", None, None, None, 0,
        ctypes.byref(out_blob),
    )
    if not ok:
        raise ctypes.WinError()
    try:
        return MAGIC_DPAPI + _blob_bytes(out_blob)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def unprotect(data):
    if data.startswith(MAGIC_PLAIN):
        return data[len(MAGIC_PLAIN):]
    if not data.startswith(MAGIC_DPAPI):
        raise ValueError("unrecognized container")
    if not IS_WINDOWS:
        raise RuntimeError("vault was encrypted on Windows")
    raw = data[len(MAGIC_DPAPI):]
    in_blob = _blob(raw)
    out_blob = _DATA_BLOB()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
    )
    if not ok:
        raise ctypes.WinError()
    try:
        return _blob_bytes(out_blob)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)
