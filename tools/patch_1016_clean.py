# -*- coding: utf-8 -*-
import io
P = "D:/123/4/android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()

# 1) remove the debug hook block entirely
start = s.index('        if (getIntent() != null && getIntent().getBooleanExtra("testdlg", false)) {')
end_marker = '            }, 1500);\n        }\n'
end = s.index(end_marker, start) + len(end_marker)
s = s[:start] + s[end:]

# 2) drop the now-unused items list in showAccMenu
old = '''        final java.util.ArrayList<String> items = new java.util.ArrayList<String>();
        items.add("导入到游戏");
        if (!a.isBackup()) items.add("重命名");
        items.add("删除");
'''
assert s.count(old) == 1
s = s.replace(old, "")

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("clean ok, testdlg:", s.count("testdlg"))
