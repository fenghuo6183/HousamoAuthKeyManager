# -*- coding: utf-8 -*-
import io
p = r"D:/123/4/android/src/com/housamo/authkey/MainActivity.java"
s = io.open(p, encoding="utf-8").read()

# 1) 移除调试钩子
hook = u'''        if (getIntent() != null && getIntent().getBooleanExtra("testexport", false)) {
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
assert s.count(hook) == 1
s = s.replace(hook, u"", 1)

# 2) 设置页导出位置初始值带游戏子目录
old = u'''        rowExportVal = value(0, exportRootLabel());'''
new = u'''        rowExportVal = value(0, exportRootLabelFull());'''
assert s.count(old) == 1
s = s.replace(old, new, 1)

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("cleaned")
