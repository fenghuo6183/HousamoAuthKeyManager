# -*- coding: utf-8 -*-
import io
p = r'D:/123/4/android/AndroidManifest.xml'
s = io.open(p, encoding='utf-8').read()
assert 'android:versionCode="16"' in s
s = s.replace('android:versionCode="16"', 'android:versionCode="17"').replace('android:versionName="1.0.15"', 'android:versionName="1.0.16"')
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)

p = r'D:/123/4/android/build_apk.py'
s = io.open(p, encoding='utf-8').read()
assert 'VERSION_CODE = "16"' in s
s = s.replace('VERSION_CODE = "16"', 'VERSION_CODE = "17"').replace('VERSION_NAME = "1.0.15"', 'VERSION_NAME = "1.0.16"')
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('bumped ok')
