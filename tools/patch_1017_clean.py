# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()

start = s.find("    private void dbgImportHook() {")
end_marker = "    @Override\n    protected void onCreate(Bundle savedInstanceState) {"
end = s.find(end_marker)
assert start > 0 and end > start, (start, end)
s = s[:start] + end_marker + s[end + len(end_marker):]

hook = """        new android.os.Handler().postDelayed(new Runnable() {
            public void run() { dbgImportHook(); }
        }, 1500);
"""
assert hook in s
s = s.replace(hook, "", 1)

assert "dbgImportHook" not in s
io.open(P, "w", encoding="utf-8").write(s)
print("hooks removed", len(s))
