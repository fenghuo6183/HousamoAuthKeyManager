# -*- coding: utf-8 -*-
import io
P = "D:/123/4/android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
bad = '\n        if (getIntent() != null && getIntent().hasExtra("testgame")) applyGame(gameById(getIntent().getStringExtra("testgame"))); // TEMP-DEBUG'
assert s.count(bad) == 1
s = s.replace(bad, "")
io.open(P, "w", encoding="utf-8").write(s)
assert "TEMP-DEBUG" not in s
print("hook removed")
