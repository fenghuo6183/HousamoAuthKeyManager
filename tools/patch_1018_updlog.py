# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
old = '''                runOnUiThread(new Runnable() {
                    public void run() {
                        if (rowUpdateVal != null) {
                            rowUpdateVal.setText(cmp > 0 ? "发现 " + ver + "，点此更新" : "已是最新版 " + CURRENT_VER);'''
new = '''                runOnUiThread(new Runnable() {
                    public void run() {
                        log("[更新] 本地 " + CURRENT_VER + " / 远端 " + (ver.length() == 0 ? "读取失败" : ver) + (apkUrl == null ? "（无 APK 资产）" : ""));
                        if (rowUpdateVal != null) {
                            rowUpdateVal.setText(cmp > 0 ? "发现 " + ver + "，点此更新" : "已是最新版 " + CURRENT_VER);'''
assert s.count(old) == 1
s = s.replace(old, new)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("ok")