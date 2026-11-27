# -*- coding: utf-8 -*-
"""Startup reconcile: is the key the device is running already in our vault?"""
from __future__ import annotations

import hashlib

from . import game as game_mod


def digest_of(key_bytes):
    return hashlib.sha256(game_mod.clean_key(key_bytes)).hexdigest()


def is_known(vault, digest):
    if vault is None:
        return True
    return any(e.get("sha256") == digest for e in vault.entries)


def should_prompt(vault, key_bytes, ignored):
    digest = digest_of(key_bytes)
    if digest in set(ignored or []):
        return False, digest
    return (not is_known(vault, digest)), digest
