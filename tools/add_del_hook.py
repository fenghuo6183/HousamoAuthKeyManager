# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
old = """    private void dbgImportHook() {
        if (getIntent() == null) return;"""
assert old in s
s = s.replace(old, """    private void dbgImportHook() {
        if (getIntent() == null) return;
        if (getIntent().getBooleanExtra("testdel", false)) {
            for (int i = accounts.size() - 1; i >= 0; i--) {
                if (accounts.get(i).name.startsWith("测试号")) {
                    log("[test] 删除测试账号 " + accounts.get(i).name);
                    accounts.remove(i);
                }
            }
            saveVault();
            refreshList();
            refreshAccountsView();
            toast("测试账号已删");
            return;
        }""", 1)
io.open(P, "w", encoding="utf-8").write(s)
print("del hook added")
