# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
old = '        else if ("upd".equals(k)) { showPage(3); checkUpdate(true); }'
new = '''        else if ("upd".equals(k)) { showPage(3); checkUpdate(true); }
        else if ("imp".equals(k)) {
            showPage(2);
            final Account acc = firstRealAccount();
            if (acc == null) { toast("no account"); return; }
            new android.os.Handler().postDelayed(new Runnable() {
                public void run() { doImportNow(acc); }
            }, 4000);
        }
        else if ("undo2".equals(k)) {
            new android.os.Handler().postDelayed(new Runnable() {
                public void run() {
                    String cur = readKeyAt(EXT_KEY);
                    undoImport(cur, "测试撤销");
                }
            }, 4000);
        }'''
assert s.count(old) == 1
s = s.replace(old, new)

# helper
old2 = '    private void dbgDialog(String k) {'
new2 = '''    private Account firstRealAccount() {
        for (Account a : accounts) if (!a.isBackup() && inGame(a)) return a;
        return null;
    }

    private void dbgDialog(String k) {'''
assert s.count(old2) == 1
s = s.replace(old2, new2)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("ok")