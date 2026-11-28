# -*- coding: utf-8 -*-
import io, re
P = "D:/123/4/android/src/com/housamo/authkey/MainActivity.java"
lines = io.open(P, encoding="utf-8").read().split("\n")
i = next(k for k, l in enumerate(lines) if l.strip().startswith('if (getIntent() != null && getIntent().getBooleanExtra("testdlg"'))
j = next(k for k in range(i, len(lines)) if lines[k].strip() == "}, 1500);")
body = '''        if (getIntent() != null && getIntent().getBooleanExtra("testdlg", false)) {
            final String m = getIntent().getStringExtra("testdlgmode");
            showPage("accmenu".equals(m) || "copymenu".equals(m) || "rename".equals(m)
                    || "delete".equals(m) || "import".equals(m) || "done".equals(m) ? 2 : 1);
            new android.os.Handler(getMainLooper()).postDelayed(new Runnable() {
                public void run() {
                    if ("shizuku".equals(m)) { showShizukuGuide(); return; }
                    if ("pc".equals(m)) { showPcGuide(); return; }
                    if ("noperm".equals(m)) { showNoPerm(); return; }
                    if ("update".equals(m)) { showUpdatePrompt("1.9.9", "https://github.com/fenghuo6183/HousamoAuthKeyManager/releases/latest"); return; }
                    refreshAccountsView();
                    log("[test] accView=" + accView.size());
                    if (accView.isEmpty()) return;
                    list.setItemChecked(0, true);
                    updateState();
                    final Account a0 = selected();
                    log("[test] sel=" + (a0 == null ? "null" : a0.name));
                    if (a0 == null) return;
                    if ("accmenu".equals(m)) showAccMenu();
                    else if ("copymenu".equals(m)) startCopyMove();
                    else if ("rename".equals(m)) doRename();
                    else if ("delete".equals(m)) doDelete();
                    else if ("import".equals(m)) doImport();
                    else if ("done".equals(m)) doImportNow(a0);
                }
            }, 1500);
        }'''.split("\n")
lines[i:j + 1] = body
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("ok")
