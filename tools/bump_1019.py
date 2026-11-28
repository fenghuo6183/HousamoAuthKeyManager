# -*- coding: utf-8 -*-
import io
m = "android/AndroidManifest.xml"
s = io.open(m, encoding="utf-8").read()
assert 'android:versionCode="19"' in s and 'android:versionName="1.0.18"' in s
s = s.replace('android:versionCode="19"', 'android:versionCode="20"').replace('android:versionName="1.0.18"', 'android:versionName="1.0.19"')
io.open(m, "w", encoding="utf-8", newline="\n").write(s)
b = "android/build_apk.py"
t = io.open(b, encoding="utf-8").read()
t = t.replace('VERSION_CODE = "19"', 'VERSION_CODE = "20"').replace('VERSION_NAME = "1.0.18"', 'VERSION_NAME = "1.0.19"')
io.open(b, "w", encoding="utf-8", newline="\n").write(t)
print("bumped")
