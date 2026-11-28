# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
bad = '''    private void recordImportHistory(a.name, prevKey, a.key, histBackup);
            String raw = sp.getString("importHistory", "[]");'''
good = '''    private void recordImportHistory(String toName, String prevKey, String targetKey, String backupName) {
        try {
            SharedPreferences sp = getPreferences(MODE_PRIVATE);
            String raw = sp.getString("importHistory", "[]");'''
assert s.count(bad) == 1, s.count(bad)
s = s.replace(bad, good)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("repaired")
