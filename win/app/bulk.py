# -*- coding: utf-8 -*-
"""Bulk import/export, backup retention and import history (Android parity)."""
from __future__ import annotations

import os
import re
import time
import zipfile

from .game import fingerprint

KEEP_BACKUPS = ("all", "10", "30d")
KEEP_LABELS = {"all": "全部保留", "10": "最近 10 份", "30d": "最近 30 天"}
_UNSAFE = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def import_items(vault, items, source="", device=""):
    """Add every scanned key to the account section. Returns (added, skipped)."""
    added, skipped = [], 0
    for item in items:
        _entry, created = vault.add(name=item.get("name") or "导入的账号",
                                    key=item["key"],
                                    source=source or item.get("path", ""),
                                    device=device, kind="account")
        if created:
            added.append(_entry)
        else:
            skipped += 1
    return added, skipped


def safe_folder(name, fallback="account"):
    text = _UNSAFE.sub("_", (name or "").strip()).strip(". ")
    return text[:60] or fallback


def export_all(vault, target_path, game_label, kind="account"):
    """Zip every entry of one section, each in its own folder plus a manifest."""
    entries = vault.by_kind(kind)
    used = set()
    lines = ["# %s 导出" % game_label,
             "名称	指纹	字节数	添加时间	备注"]
    folders = os.path.dirname(os.path.abspath(target_path))
    if folders:
        os.makedirs(folders, exist_ok=True)
    with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for index, entry in enumerate(entries, 1):
            key = vault.key_of(entry)
            folder = safe_folder(entry.get("name"), "account-%d" % index)
            base = folder
            bump = 2
            while folder.lower() in used:
                folder = "%s (%d)" % (base, bump)
                bump += 1
            used.add(folder.lower())
            zf.writestr(folder + "/AuthKey.txt", key)
            lines.append("%s	%s	%d	%s	%s" % (
                entry.get("name") or folder, entry.get("fingerprint") or fingerprint(key),
                len(key), entry.get("created_at") or "",
                (entry.get("note") or "").replace("\t", " ").replace("\n", " ")))
        zf.writestr("manifest.txt", "\n".join(lines) + "\n")
    return len(entries)


def _stamp(entry):
    try:
        return time.mktime(time.strptime(entry.get("created_at") or "", "%Y-%m-%d %H:%M:%S"))
    except (ValueError, TypeError):
        return None


def prune_backups(vault, policy="all", now=None):
    """Drop old automatic backups. Returns the ids that were removed."""
    if policy not in KEEP_BACKUPS or policy == "all":
        return []
    backups = vault.by_kind("backup")
    keep_ids = set()
    if policy == "10":
        ordered = sorted(backups, key=lambda e: _stamp(e) or 0, reverse=True)
        keep_ids = {e["id"] for e in ordered[:10]}
    else:
        cutoff = (now or time.time()) - 30 * 86400
        for entry in backups:
            stamp = _stamp(entry)
            if stamp is None or stamp >= cutoff:
                keep_ids.add(entry["id"])
    removed = []
    for entry in list(backups):
        if entry["id"] not in keep_ids:
            if vault.delete(entry["id"]):
                removed.append(entry["id"])
    return removed


# -- import history (settings.json) ------------------------------------
def record_import(settings, game_id, entry, backup_id=""):
    table = dict(settings.get("import_history") or {})
    items = list(table.get(game_id) or [])
    items.insert(0, {"at": time.strftime("%Y-%m-%d %H:%M:%S"),
                     "entry_id": entry.get("id", ""),
                     "name": entry.get("name", ""),
                     "fingerprint": entry.get("fingerprint", ""),
                     "backup_id": backup_id or ""})
    table[game_id] = items[:20]
    settings.set("import_history", table)
    return table[game_id]


def import_history(settings, game_id, limit=5):
    return list((settings.get("import_history") or {}).get(game_id) or [])[:limit]


def last_import(settings, game_id):
    items = import_history(settings, game_id, 1)
    return items[0] if items else None


def forget_import(settings, game_id):
    table = dict(settings.get("import_history") or {})
    items = list(table.get(game_id) or [])
    if items:
        items.pop(0)
    table[game_id] = items
    settings.set("import_history", table)
    return table[game_id]
