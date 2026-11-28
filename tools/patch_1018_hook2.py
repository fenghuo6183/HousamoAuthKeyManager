# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
old = '        } else if ("zip".equals(k)) { showPage(1); startZipExport(); }'
new = '        } else if ("zip".equals(k)) { showPage(1); startZipExport(); }\n        else if ("upd".equals(k)) { showPage(3); checkUpdate(true); }'
assert s.count(old) == 1
s = s.replace(old, new)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("ok")