# -*- coding: utf-8 -*-
import io
p1 = r"D:/123/4/android/AndroidManifest.xml"
s = io.open(p1, encoding="utf-8").read()
assert s.count('android:versionCode="14"') == 1
assert s.count('android:versionName="1.0.13"') == 1
s = s.replace('android:versionCode="14"', 'android:versionCode="15"').replace('android:versionName="1.0.13"', 'android:versionName="1.0.14"')
io.open(p1, "w", encoding="utf-8", newline="\n").write(s)

p2 = r"D:/123/4/android/build_apk.py"
t = io.open(p2, encoding="utf-8").read()
assert t.count('VERSION_CODE = "14"') == 1
assert t.count('VERSION_NAME = "1.0.13"') == 1
t = t.replace('VERSION_CODE = "14"', 'VERSION_CODE = "15"').replace('VERSION_NAME = "1.0.13"', 'VERSION_NAME = "1.0.14"')
io.open(p2, "w", encoding="utf-8", newline="\n").write(t)
print("bumped")
