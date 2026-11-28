# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
old = "    @Override\n    private void dbgImportHook() {"
assert old in s
s = s.replace(old, "    private void dbgImportHook() {", 1)
old2 = "    protected void onCreate(Bundle savedInstanceState) {"
assert old2 in s
s = s.replace(old2, "    @Override\n" + old2, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("fixed override")
