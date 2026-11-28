# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
old = """    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);"""
assert old in s
s = s.replace(old, """    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        dbgImportHook();""", 1)
io.open(P, "w", encoding="utf-8").write(s)
print("hook called")
