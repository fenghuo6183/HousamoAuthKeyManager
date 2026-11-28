# -*- coding: utf-8 -*-
import io
path = r"D:/123/4/win/qtui/pages.py"
with io.open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
assert lines[455].startswith("CONNECT_PROFILES = ("), lines[455]
assert lines[710].strip() == "page.add(panel)", lines[710]
with io.open(r"D:/123/4/win/.tmp_connect_block.py", "r", encoding="utf-8") as f:
    block = f.read().splitlines(True)
if not block[-1].endswith("\n"):
    block[-1] += "\n"
new = lines[:455] + block + lines[711:]
with io.open(path, "w", encoding="utf-8", newline="") as f:
    f.writelines(new)
print("old lines", len(lines), "new lines", len(new))
