# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
old = """        super.onCreate(savedInstanceState);
        dbgImportHook();"""
assert old in s
s = s.replace(old, """        super.onCreate(savedInstanceState);
        new android.os.Handler().postDelayed(new Runnable() {
            public void run() { dbgImportHook(); }
        }, 1500);""", 1)
io.open(P, "w", encoding="utf-8").write(s)
print("hook delayed")
