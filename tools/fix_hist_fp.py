# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()

old_sig = '    private void recordImportHistory(String toName, String prevKey, String backupName) {'
new_sig = '    private void recordImportHistory(String toName, String prevKey, String targetKey, String backupName) {'
assert s.count(old_sig) == 1
s = s.replace(old_sig, new_sig)

old_line = '            o.put("toFp", hash(toName).length());'
new_line = '            o.put("toFp", hash(targetKey == null ? "" : targetKey).substring(0, 16));'
assert s.count(old_line) == 1
s = s.replace(old_line, new_line)

import re
m = re.search(r'recordImportHistory\(([^;]*?)\);', s)
print("callsite:", m.group(0) if m else None)
old_call = m.group(0)
new_call = 'recordImportHistory(a.name, prevKey, a.key, histBackup);'
s = s.replace(old_call, new_call, 1)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("ok")