# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()

old1 = '''            if (dbgShotOff) {
                getWindow().clearFlags(android.view.WindowManager.LayoutParams.FLAG_SECURE);
                return;
            }
'''
assert s.count(old1) == 1
s = s.replace(old1, "")

old2 = '''    private boolean dbgShotOff = false;

'''
assert s.count(old2) == 1
s = s.replace(old2, "")

old3 = '''        if (getIntent() != null && getIntent().getBooleanExtra("shotoff", false)) dbgShotOff = true;
'''
assert s.count(old3) == 1
s = s.replace(old3, "")

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("hook removed", "shotoff" in s, "dbgShotOff" in s)
