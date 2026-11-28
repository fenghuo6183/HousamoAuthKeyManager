# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()

old = '''    private void applyShotFlag() {
        try {'''
new = '''    private void applyShotFlag() {
        try {
            if (dbgShotOff) {
                getWindow().clearFlags(android.view.WindowManager.LayoutParams.FLAG_SECURE);
                return;
            }'''
assert s.count(old) == 1
s = s.replace(old, new)

old2 = '''    private boolean noShot() {'''
new2 = '''    private boolean dbgShotOff = false;

    private boolean noShot() {'''
assert s.count(old2) == 1
s = s.replace(old2, new2)

old3 = '''        super.onCreate(savedInstanceState);
        applyGame('''
new3 = '''        super.onCreate(savedInstanceState);
        if (getIntent() != null && getIntent().getBooleanExtra("shotoff", false)) dbgShotOff = true;
        applyGame('''
assert s.count(old3) == 1
s = s.replace(old3, new3)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("hook added")