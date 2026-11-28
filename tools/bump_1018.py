# -*- coding: utf-8 -*-
import io
P="android/src/com/housamo/authkey/MainActivity.java"
s=io.open(P,encoding="utf-8").read()
assert s.count('CURRENT_VER = "1.0.17"')==1
s=s.replace('CURRENT_VER = "1.0.17"','CURRENT_VER = "1.0.18"')
# call home overview refresh from updateState
old='''    private void updateState() {
        boolean gameInstalled = isInstalled(PKG);'''
new='''    private void updateState() {
        refreshHomeOverview();
        boolean gameInstalled = isInstalled(PKG);'''
assert s.count(old)==1
s=s.replace(old,new)
io.open(P,"w",encoding="utf-8",newline="\n").write(s)
print("ok")