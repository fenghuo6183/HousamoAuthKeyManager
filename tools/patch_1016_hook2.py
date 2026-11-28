# -*- coding: utf-8 -*-
import io
P = "D:/123/4/android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
old = '''        if (getIntent() != null && getIntent().getBooleanExtra("testdlg", false)) {
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
'''
new = '''        if (getIntent() != null && getIntent().getBooleanExtra("testdlg", false)) {
            final String m = getIntent().getStringExtra("testdlgmode");
            showPage("accmenu".equals(m) || "copymenu".equals(m) || "rename".equals(m)
                    || "delete".equals(m) || "import".equals(m) || "done".equals(m) ? 2 : 1);
            new android.os.Handler(getMainLooper()).postDelayed(new Runnable() {
                public void run() {
                    if ("shizuku".equals(m)) { showShizukuGuide(); return; }
                    if ("pc".equals(m)) { showPcGuide(); return; }
                    if ("noperm".equals(m)) { showNoPerm(); return; }
                    if ("update".equals(m)) { showUpdatePrompt("1.9.9", "https://github.com/fenghuo6183/HousamoAuthKeyManager/releases/latest"); return; }
                    if (accounts.isEmpty()) { log("[test] 账号库是空的"); return; }
                    selectAccount(accounts.get(0));
                    if ("accmenu".equals(m)) showAccMenu();
                    else if ("copymenu".equals(m)) startCopyMove();
                    else if ("rename".equals(m)) doRename();
                    else if ("delete".equals(m)) doDelete();
                    else if ("import".equals(m)) doImport();
                    else if ("done".equals(m)) doImportNow(accounts.get(0));
                }
            }, 1500);
        }
'''
assert s.count(old) == 1
s = s.replace(old, new)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("hook ok")
