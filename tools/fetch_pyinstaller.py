# -*- coding: utf-8 -*-
"""Fetch PyInstaller and its pure-python deps as wheels, unpack into .tools/pylibs.

pip cannot write its unpack temp dirs on this host, so we install by hand.
"""
import json
import os
import sys
import urllib.request
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIBS = os.path.join(ROOT, ".tools", "pylibs")
DL = os.path.join(ROOT, ".tools", "wheels")

PKGS = ["pyinstaller", "pyinstaller-hooks-contrib", "altgraph", "pefile",
        "pywin32-ctypes", "packaging", "setuptools"]

PY = "cp%d%d" % (sys.version_info[0], sys.version_info[1])


def pick(meta):
    files = meta["urls"]
    cands = []
    for f in files:
        name = f["filename"]
        if not name.endswith(".whl"):
            continue
        if f.get("yanked"):
            continue
        tags = name[:-4].split("-")[-3:]
        py_tag, abi, plat = tags[0], tags[1], tags[2]
        ok_py = py_tag.startswith("py3") or py_tag.startswith(PY) or py_tag.startswith("cp3")
        ok_plat = plat in ("any", "win_amd64")
        if ok_py and ok_plat:
            cands.append((0 if plat != "any" else 1, f))
    if not cands:
        return None
    cands.sort(key=lambda x: (x[0], x[1]["filename"]))
    return cands[0][1]


def main():
    os.makedirs(LIBS, exist_ok=True)
    os.makedirs(DL, exist_ok=True)
    for pkg in PKGS:
        try:
            with urllib.request.urlopen("https://pypi.org/pypi/%s/json" % pkg, timeout=40) as r:
                meta = json.load(r)
        except Exception as e:
            print("[skip]", pkg, e)
            continue
        f = pick(meta)
        if not f:
            print("[skip]", pkg, "no wheel")
            continue
        dst = os.path.join(DL, f["filename"])
        if not os.path.exists(dst):
            with urllib.request.urlopen(f["url"], timeout=120) as r, open(dst, "wb") as o:
                o.write(r.read())
        with zipfile.ZipFile(dst) as z:
            z.extractall(LIBS)
        print("[ok]", pkg, f["filename"])
    print("LIBS:", LIBS)


if __name__ == "__main__":
    main()
