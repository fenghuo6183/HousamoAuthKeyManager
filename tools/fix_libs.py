# -*- coding: utf-8 -*-
import io
P="android/build_apk.py"
s=io.open(P,encoding="utf-8").read()
old='"annotation.jar")]'
new='"annotation.jar", "zxing-core.jar")]'
assert s.count(old)==1
s=s.replace(old,new)
io.open(P,"w",encoding="utf-8",newline="\n").write(s)
print("ok")