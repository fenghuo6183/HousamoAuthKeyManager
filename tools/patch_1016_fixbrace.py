# -*- coding: utf-8 -*-
import io
P = "D:/123/4/android/src/com/housamo/authkey/MainActivity.java"
lines = io.open(P, encoding="utf-8").read().split("\n")
for i in range(len(lines) - 2):
    if lines[i].strip() == "}, 1500);" and lines[i + 1].strip() == "}" and lines[i + 2].strip() == "}":
        del lines[i + 2]
        print("removed extra brace at", i + 3)
        break
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
