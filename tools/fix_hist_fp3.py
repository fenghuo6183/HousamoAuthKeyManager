# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
old = 'if (prevKey != null && prevKey.length() >= 8) recordImportHistory(a.name, prevKey, histBackup);'
new = 'if (prevKey != null && prevKey.length() >= 8) recordImportHistory(a.name, prevKey, a.key, histBackup);'
assert s.count(old) == 1
s = s.replace(old, new)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("ok")