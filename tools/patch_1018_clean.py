# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()

old1 = '''        if (getIntent() != null && getIntent().getBooleanExtra("testdark", false)) {
            getPreferences(MODE_PRIVATE).edit().putBoolean("night", true).apply();
        }
        if (getIntent() != null && getIntent().getBooleanExtra("testlight", false)) {
            getPreferences(MODE_PRIVATE).edit().putBoolean("night", false).apply();
        }
'''
assert s.count(old1) == 1
s = s.replace(old1, "")

old2 = '''        final String tdlg = getIntent() == null ? null : getIntent().getStringExtra("testdlg");
        if (tdlg != null) {
            new android.os.Handler().postDelayed(new Runnable() {
                public void run() { dbgDialog(tdlg); }
            }, 1500);
        }
'''
assert s.count(old2) == 1
s = s.replace(old2, "")

start = s.index("    private Account firstRealAccount() {")
end = s.index("    private void showLanTransfer() {")
block = s[start:end]
assert "dbgDialog" in block, block[:200]
s = s[:start] + s[end:]

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
for k in ["testdark", "testlight", "testdlg", "dbgDialog", "firstRealAccount", "undo2"]:
    print(k, k in s)
print("len", len(s))