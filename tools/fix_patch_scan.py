# -*- coding: utf-8 -*-
import io
P = "tools/patch_1017_scan.py"
s = io.open(P, encoding="utf-8").read()
s = s.replace("    protected void onCreate(android.os.Bundle b) {", "    protected void onCreate(Bundle savedInstanceState) {")
io.open(P, "w", encoding="utf-8").write(s)
print("fixed patch")
