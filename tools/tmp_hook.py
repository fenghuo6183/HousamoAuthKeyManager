# -*- coding: utf-8 -*-
import io
P = "D:/123/4/android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
a = '        applyGame(gameById(getPreferences(MODE_PRIVATE).getString("gameId", "housamo")));'
assert s.count(a) == 1
s = s.replace(a, a + '\n        if (getIntent() != null && getIntent().hasExtra("testgame")) applyGame(gameById(getIntent().getStringExtra("testgame"))); // TEMP-DEBUG')
io.open(P, "w", encoding="utf-8").write(s)
print("hook in")
