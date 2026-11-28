# -*- coding: utf-8 -*-
import io
P = "D:/123/4/android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
old = '''                    if (accounts.isEmpty()) { log("[test] 账号库是空的"); return; }
                    selectAccount(accounts.get(0));'''
new = '''                    if (accounts.isEmpty()) { log("[test] 账号库是空的"); return; }
                    refreshAccountsView();
                    int idx0 = accView.indexOf(accounts.get(0));
                    log("[test] accView=" + accView.size() + " idx=" + idx0);
                    if (idx0 >= 0) { list.setItemChecked(idx0, true); updateState(); }
                    log("[test] sel=" + (selected() == null ? "null" : selected().name));'''
assert s.count(old) == 1
s = s.replace(old, new)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
