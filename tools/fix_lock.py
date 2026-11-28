# -*- coding: utf-8 -*-
import io
P="android/src/com/housamo/authkey/MainActivity.java"
s=io.open(P,encoding="utf-8").read()
old='''                h2[0] = showCard(d);
                h[0] = showCard(c);'''
new='''                h2[0] = showCard(d);'''
assert s.count(old)==1
s=s.replace(old,new)
io.open(P,"w",encoding="utf-8",newline="\n").write(s)
print("ok")