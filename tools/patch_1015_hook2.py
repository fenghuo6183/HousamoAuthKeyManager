# -*- coding: utf-8 -*-
import io
p = r'D:/123/4/android/src/com/housamo/authkey/MainActivity.java'
s = io.open(p, encoding='utf-8').read()

# debug flag field
a0 = u'    private LinearLayout permBox = null;'
assert s.count(a0) == 1, 'field'
s = s.replace(a0, a0 + u'\n    private boolean debugNoPerm = false;', 1)

# permReady honors debug flag
a1 = u'''    private boolean permReady() {
        return hasRoot || shizukuReady();
    }'''
assert s.count(a1) == 1, 'permReady'
s = s.replace(a1, u'''    private boolean permReady() {
        if (debugNoPerm) return false;
        return hasRoot || shizukuReady();
    }''', 1)

# rework hook
old_hook = u'''            hasRoot = false; shizukuBinder = false; shizukuGranted = false; rootChecked = true;
            showPage(0);
            updateState();'''
assert s.count(old_hook) == 1, 'hook body'
s = s.replace(old_hook, u'''            debugNoPerm = true; hasRoot = false; rootChecked = true;
            showPage(1);
            updateState();''', 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('hook v2 ok')
