# -*- coding: utf-8 -*-
"""Encrypted multi-account key vault (one file per game)."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import uuid

from . import dpapi

VAULT_VERSION = 1
HAK_FORMAT = "housamo-authkey-backup"
HAK_VERSION = 2
LEGACY_NAME = "vault.dat"


def vault_path_for(game_id):
    from .config import app_dir
    folder = app_dir()
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "vault.%s.dat" % game_id)


def default_vault_path(game_id="housamo"):
    return vault_path_for(game_id)


def migrate_legacy_vault():
    """Rename the pre-1.2 single vault into the Housamo vault exactly once."""
    from .config import app_dir
    folder = app_dir()
    legacy = os.path.join(folder, LEGACY_NAME)
    target = os.path.join(folder, "vault.housamo.dat")
    if os.path.exists(legacy) and not os.path.exists(target):
        try:
            os.replace(legacy, target)
            return True
        except OSError:
            return False
    return False


def _fp(text):
    if len(text) <= 8:
        return text
    return "%s\u2026%s (%d)" % (text[:4], text[-4:], len(text))


class Vault:
    def __init__(self, path=None, game_id="housamo"):
        self.game_id = game_id
        self.path = path or default_vault_path(game_id)
        self.entries = []
        self.load()

    # -- persistence ---------------------------------------------------
    def load(self):
        self.entries = []
        if not os.path.exists(self.path):
            return
        with open(self.path, "rb") as fh:
            raw = fh.read()
        if not raw:
            return
        try:
            payload = json.loads(dpapi.unprotect(raw).decode("utf-8"))
            self.entries = payload.get("entries", [])
        except Exception as exc:
            raise RuntimeError("账号库无法解密（文件可能被复制到了别的电脑）：%s" % exc)
        for entry in self.entries:
            entry.setdefault("kind", "account")
            entry.setdefault("game", self.game_id)

    def save(self):
        payload = {"version": VAULT_VERSION, "entries": self.entries}
        raw = json.dumps(payload, ensure_ascii=False, indent=1).encode("utf-8")
        data = dpapi.protect(raw)
        tmp = self.path + ".tmp"
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, self.path)

    # -- entries -------------------------------------------------------
    def by_kind(self, kind):
        return [e for e in self.entries if e.get("kind", "account") == kind]

    def add(self, name, key, note="", source="", device="", kind="account", game=None):
        key = bytes(key)
        text = key.decode("utf-8", "replace")
        digest = hashlib.sha256(key).hexdigest()
        for entry in self.entries:
            if entry.get("sha256") == digest:
                return entry, False
        entry = {
            "id": uuid.uuid4().hex[:12],
            "name": name or "未命名账号",
            "note": note,
            "key_b64": base64.b64encode(key).decode("ascii"),
            "fingerprint": _fp(text),
            "sha256": digest,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": source,
            "device": device,
            "kind": kind if kind in ("account", "backup") else "account",
            "game": game or self.game_id,
        }
        self.entries.insert(0, entry)
        self.save()
        return entry, True

    def get(self, entry_id):
        for entry in self.entries:
            if entry.get("id") == entry_id:
                return entry
        return None

    def key_of(self, entry):
        return base64.b64decode(entry["key_b64"])

    def update(self, entry_id, **fields):
        entry = self.get(entry_id)
        if not entry:
            return None
        for key in ("name", "note"):
            if key in fields and fields[key] is not None:
                entry[key] = fields[key]
        self.save()
        return entry

    def delete(self, entry_id):
        before = len(self.entries)
        self.entries = [e for e in self.entries if e.get("id") != entry_id]
        if len(self.entries) != before:
            self.save()
            return True
        return False

    # -- portable .hak files -------------------------------------------
    def export_hak(self, entry_id, path, include_key=True):
        entry = self.get(entry_id)
        if not entry:
            raise KeyError("账号不存在")
        payload = {
            "format": HAK_FORMAT,
            "version": HAK_VERSION,
            "game": entry.get("game") or self.game_id,
            "kind": entry.get("kind", "account"),
            "name": entry.get("name"),
            "note": entry.get("note", ""),
            "key_b64": entry.get("key_b64") if include_key else "",
            "fingerprint": entry.get("fingerprint"),
            "created_at": entry.get("created_at"),
            "source": entry.get("source", ""),
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        return payload

    def read_hak(self, path):
        """Parse a .hak file without touching the vault yet."""
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        if payload.get("format") != HAK_FORMAT:
            raise ValueError("不是有效的 .hak 备份文件")
        if not payload.get("key_b64"):
            raise ValueError("这个 .hak 文件里没有 key（可能是只读导出）")
        owner = payload.get("game") or ""
        if owner and owner != self.game_id:
            from .game import game_by_id
            raise ValueError("这个备份属于「%s」，请先切换到该游戏再导入。"
                             % game_by_id(owner).label)
        return payload, base64.b64decode(payload["key_b64"])

    def add_hak_payload(self, payload, key):
        entry, created = self.add(
            name=payload.get("name") or "导入的账号",
            key=key,
            note=payload.get("note", ""),
            source=payload.get("source", "hak"),
            kind=payload.get("kind", "account"),
            game=payload.get("game") or self.game_id,
        )
        return entry, created

    def import_hak(self, path):
        payload, key = self.read_hak(path)
        return self.add_hak_payload(payload, key)

    def find_same(self, key):
        """Entry holding exactly this key, if any."""
        digest = hashlib.sha256(bytes(key)).hexdigest()
        for entry in self.entries:
            if entry.get("sha256") == digest:
                return entry
        return None

    def find_by_name(self, name):
        for entry in self.entries:
            if (entry.get("name") or "") == name:
                return entry
        return None

    def replace_key(self, entry_id, key):
        """Swap one entry's key in place; the old key becomes a backup entry."""
        entry = self.get(entry_id)
        if not entry:
            return None, None
        key = bytes(key)
        digest = hashlib.sha256(key).hexdigest()
        if entry.get("sha256") == digest:
            return entry, None
        old_key = self.key_of(entry)
        old_fp = entry.get("fingerprint") or ""
        entry["key_b64"] = base64.b64encode(key).decode("ascii")
        entry["fingerprint"] = _fp(key.decode("utf-8", "replace"))
        entry["sha256"] = digest
        entry["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        self.save()
        backup, _ = self.add(
            name=(entry.get("name") or "账号") + " 换 key 前的旧 key",
            key=old_key,
            note="旧指纹 %s" % old_fp,
            source="replace", kind="backup",
            game=entry.get("game") or self.game_id)
        return entry, backup
