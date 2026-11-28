# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, ("anchor %d: %r" % (s.count(old), old[:80]))
    s = s.replace(old, new, cnt)

rep('''        super.onCreate(savedInstanceState);
        applyGame(gameById(getPreferences(MODE_PRIVATE).getString("gameId", "housamo")));''',
    '''        super.onCreate(savedInstanceState);
        if (getIntent() != null && getIntent().getBooleanExtra("testdark", false)) {
            getPreferences(MODE_PRIVATE).edit().putBoolean("night", true).apply();
        }
        if (getIntent() != null && getIntent().getBooleanExtra("testlight", false)) {
            getPreferences(MODE_PRIVATE).edit().putBoolean("night", false).apply();
        }
        applyGame(gameById(getPreferences(MODE_PRIVATE).getString("gameId", "housamo")));''')

rep('''        if (startPage >= 0 && startPage <= 3) showPage(startPage);''',
    '''        if (startPage >= 0 && startPage <= 3) showPage(startPage);
        final String tdlg = getIntent() == null ? null : getIntent().getStringExtra("testdlg");
        if (tdlg != null) {
            new android.os.Handler().postDelayed(new Runnable() {
                public void run() { dbgDialog(tdlg); }
            }, 1500);
        }''')

anchor = '    private void showLanTransfer() {'
hook = '''    private void dbgDialog(String k) {
        if ("history".equals(k)) { showPage(3); showImportHistory(); }
        else if ("keep".equals(k)) { showPage(3); chooseBackupKeep(); }
        else if ("lock".equals(k)) { showPage(3); lockMenu(); }
        else if ("lan".equals(k)) { showPage(3); showLanTransfer(); }
        else if ("qr".equals(k)) {
            showPage(2);
            Account acc = null;
            for (Account a : accounts) if (!a.isBackup() && inGame(a)) { acc = a; break; }
            if (acc != null) makeQr(acc); else toast("no account");
        } else if ("zip".equals(k)) { showPage(1); startZipExport(); }
        else if ("clip".equals(k)) {
            try {
                android.content.ClipboardManager cm = (android.content.ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
                String key = "0123456789abcdef0123456789abcdef0123";
                cm.setPrimaryClip(android.content.ClipData.newPlainText("k", key));
            } catch (Throwable ignored) {}
            showPage(1);
            importFromClipboard();
        }
    }

'''
rep(anchor, hook + anchor)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("ok")