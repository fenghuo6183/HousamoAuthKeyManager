# -*- coding: utf-8 -*-
import io, re
p = r'D:/123/4/android/src/com/housamo/authkey/MainActivity.java'
s = io.open(p, encoding='utf-8').read()

a1 = u'''    private boolean debugNoPerm = false;
'''
assert s.count(a1) == 1
s = s.replace(a1, u'', 1)

a2 = u'''        if (debugNoPerm) return false;
'''
assert s.count(a2) == 1
s = s.replace(a2, u'', 1)

start = s.find(u'        if (getIntent() != null && getIntent().getBooleanExtra("testperm", false)) {')
assert start > 0
end = s.find(u'        pool.execute(new Runnable() {', start)
assert end > start
s = s[:start] + s[end:]

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('cleaned', s.count('testperm'), s.count('debugNoPerm'))
