# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
old = '''                    String cur = readKeyAt(EXT_KEY);
                    undoImport(cur, "测试撤销");'''
new = '''                    byte[] cb = readKeyAt(EXT_KEY);
                    String cur = cb == null ? null : new String(cb, "UTF-8").trim();
                    undoImport(cur, "测试撤销");'''
assert s.count(old) == 1
s = s.replace(old, new)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("ok")