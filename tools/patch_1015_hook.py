# -*- coding: utf-8 -*-
import io
p = r'D:/123/4/android/src/com/housamo/authkey/MainActivity.java'
s = io.open(p, encoding='utf-8').read()
anchor = u'''        pool.execute(new Runnable() {
            public void run() {
              try {
                android.util.Log.i("HSK", "pool started");'''
assert s.count(anchor) == 1, 'anchor'
hook = u'''        if (getIntent() != null && getIntent().getBooleanExtra("testperm", false)) {
            final String m = getIntent().getStringExtra("testpermmode");
            hasRoot = false; shizukuBinder = false; shizukuGranted = false; rootChecked = true;
            showPage(0);
            updateState();
            new android.os.Handler(getMainLooper()).postDelayed(new Runnable() {
                public void run() {
                    if ("shizuku".equals(m)) showShizukuGuide();
                    else if ("pc".equals(m)) showPcGuide();
                    else if ("noperm".equals(m)) showNoPerm();
                }
            }, 1200);
        }
''' + anchor
s = s.replace(anchor, hook, 1)
s = s.replace('static final String CURRENT_VER = "1.0.15";', 'static final String CURRENT_VER = "1.0.15";', 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('hook ok')
