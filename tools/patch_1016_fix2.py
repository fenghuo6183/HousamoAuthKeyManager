# -*- coding: utf-8 -*-
import io
P = "D:/123/4/android/src/com/housamo/authkey/MainActivity.java"
lines = io.open(P, encoding="utf-8").read().split("\n")
out = []
removed = 0
i = 0
while i < len(lines):
    s = lines[i].strip()
    if s in ("new AlertDialog.Builder(this)", "new AlertDialog.Builder(MainActivity.this)"):
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        nxt2 = lines[i + 2].strip() if i + 2 < len(lines) else ""
        if nxt.startswith(".setTitle(") and nxt2 == "LinearLayout c = dlgCard();":
            removed += 2
            i += 2
            continue
    out.append(lines[i])
    i += 1
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("removed", removed)
