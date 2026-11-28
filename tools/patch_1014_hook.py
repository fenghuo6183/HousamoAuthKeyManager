# -*- coding: utf-8 -*-
import io
p = r"D:/123/4/android/src/com/housamo/authkey/MainActivity.java"
s = io.open(p, encoding="utf-8").read()
old = u'''        maybeShowDisclaimer();
        syncFromExportFolderAsync();
'''
new = u'''        maybeShowDisclaimer();
        syncFromExportFolderAsync();
        if (getIntent() != null && getIntent().getBooleanExtra("testexport", false)) {
            final Account t0 = accounts.size() > 0 ? accounts.get(0) : null;
            pool.execute(new Runnable() {
                public void run() {
                    if (t0 == null) { runOnUiThread(new Runnable() { public void run() { log("[test] 没有账号"); } }); return; }
                    final String out = exportKeyFolder(t0.name, t0.key);
                    runOnUiThread(new Runnable() { public void run() { log("[test] 导出 " + t0.name + " -> " + out); } });
                }
            });
        }
'''
assert s.count(old) == 1
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new, 1))
print("hook in")
