# -*- coding: utf-8 -*-
import io
P = "D:/123/4/android/src/com/housamo/authkey/MainActivity.java"
lines = io.open(P, encoding="utf-8").read().split("\n")
out = []
removed = 0
for i, l in enumerate(lines):
    s = l.strip()
    if s in ("new AlertDialog.Builder(this)", "new AlertDialog.Builder(MainActivity.this)"):
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if nxt == "LinearLayout c = dlgCard();":
            removed += 1
            continue
    out.append(l)
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(out))
print("removed", removed)
