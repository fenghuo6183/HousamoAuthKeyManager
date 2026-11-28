# -*- coding: utf-8 -*-
import io
P="android/src/com/housamo/authkey/MainActivity.java"
s=io.open(P,encoding="utf-8").read()
assert s.count("public void stop() {\n            running = false;")==1
s=s.replace("public void stop() {\n            running = false;","public void halt() {\n            running = false;")
s=s.replace("srv.stop();","srv.halt();")
io.open(P,"w",encoding="utf-8",newline="\n").write(s)
print("ok")