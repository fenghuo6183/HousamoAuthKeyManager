# -*- coding: utf-8 -*-
import io
p = r'D:/123/4/android/src/com/housamo/authkey/MainActivity.java'
s = io.open(p, encoding='utf-8').read()
anchor = u'''        pool.execute(new Runnable() {
            public void run() {
              try {
                android.util.Log.i("HSK", "pool started");'''
assert s.count(anchor) == 1
hook = u'''        if (getIntent() != null && getIntent().getBooleanExtra("testdlg", false)) {
            final String m = getIntent().getStringExtra("testdlgmode");
            showPage(1);
            new android.os.Handler(getMainLooper()).postDelayed(new Runnable() {
                public void run() {
                    if ("shizuku".equals(m)) showShizukuGuide();
                    else if ("pc".equals(m)) showPcGuide();
                    else if ("noperm".equals(m)) showNoPerm();
                    else if ("update".equals(m)) showUpdatePrompt("1.9.9", "https://github.com/fenghuo6183/HousamoAuthKeyManager/releases/latest");
                }
            }, 1000);
        }
''' + anchor
s = s.replace(anchor, hook, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('hook ok')
