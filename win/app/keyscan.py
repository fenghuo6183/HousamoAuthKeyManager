# -*- coding: utf-8 -*-
"""Find AuthKeys in a folder or on the clipboard (parity with the Android app)."""
from __future__ import annotations

import os
import re

from .game import clean_key, fingerprint, looks_like_key, sha256_bytes

MAX_DEPTH = 3
MAX_BYTES = 8192
_XML_VALUE = re.compile(
    r'<string name="[^"]*(?:auth|key|token)[^"]*"\s*>([^<]+)</string>', re.I)


def _hint_name(name):
    low = name.lower()
    return ("key" in low or "auth" in low or low.endswith(".txt")
            or low.endswith(".prefs.xml") or low.endswith("playerprefs.xml")
            or os.path.splitext(low)[1] == "")


def _from_bytes(raw):
    """Return the key bytes inside a file, or b"" when it is not a key."""
    if not raw or len(raw) > MAX_BYTES:
        return b""
    if looks_like_key(raw):
        return clean_key(raw)
    text = raw.decode("utf-8", "replace")
    match = _XML_VALUE.search(text)
    if match:
        value = match.group(1).strip().encode("utf-8")
        if looks_like_key(value):
            return clean_key(value)
    return b""


def scan_folder(root, log=None):
    """Walk a folder (and a few levels below) and collect unique keys.

    Returns a list of {"name", "path", "key", "fingerprint", "digest"} dicts,
    first occurrence wins when the same key shows up twice.
    """
    found = []
    seen = set()
    root = os.path.abspath(root)
    for folder, dirs, files in os.walk(root):
        depth = os.path.relpath(folder, root).count(os.sep)
        if depth >= MAX_DEPTH:
            dirs[:] = []
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            if name.startswith(".") or not _hint_name(name):
                continue
            path = os.path.join(folder, name)
            try:
                if os.path.getsize(path) > MAX_BYTES:
                    continue
                with open(path, "rb") as fh:
                    raw = fh.read()
            except OSError:
                continue
            key = _from_bytes(raw)
            if not key:
                continue
            digest = sha256_bytes(key)
            if digest in seen:
                continue
            seen.add(digest)
            label = os.path.basename(os.path.dirname(path)) or name
            if os.path.isfile(os.path.join(root, name)) and depth == 0:
                label = os.path.splitext(name)[0]
            found.append({"name": label, "path": path, "key": key,
                          "fingerprint": fingerprint(key), "digest": digest})
    if log:
        log("扫描 %s：找到 %d 个 key" % (root, len(found)))
    return found


def parse_text(text):
    """Pull keys out of pasted text: one per line, optionally "名字<TAB>key"."""
    found = []
    seen = set()
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        name = ""
        parts = line.split()
        if len(parts) >= 2 and looks_like_key(parts[-1].encode("utf-8", "replace")):
            name = " ".join(parts[:-1]).strip()
            line = parts[-1]
        data = line.encode("utf-8", "replace")
        if not looks_like_key(data):
            continue
        key = clean_key(data)
        digest = sha256_bytes(key)
        if digest in seen:
            continue
        seen.add(digest)
        found.append({"name": name or ("粘贴 %d" % (len(found) + 1)),
                      "path": "", "key": key, "fingerprint": fingerprint(key),
                      "digest": digest})
    return found
