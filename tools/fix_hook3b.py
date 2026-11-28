# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
old = 'String cur = cb == null ? null : new String(cb, "UTF-8").trim();'
new = 'String cur = cb == null ? null : new String(cb).trim();'
assert s.count(old) == 1
s = s.replace(old, new)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("ok")