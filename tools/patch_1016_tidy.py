# -*- coding: utf-8 -*-
import io
P = "D:/123/4/android/src/com/housamo/authkey/MainActivity.java"
lines = io.open(P, encoding="utf-8").read().split("\n")

# 1) drop the leftover duplicate EditText creations
raw = "\n".join(lines)
a_old = ('        final EditText et = new EditText(this);\n'
         '        et.setSingleLine(true);\n'
         '        et.setInputType(InputType.TYPE_CLASS_TEXT);\n'
         '        et.setText(defName);\n'
         '        et.setSelection(defName.length());\n')
a_new = ''
b_old = ('        final EditText et = new EditText(this);\n'
         '        et.setInputType(InputType.TYPE_CLASS_TEXT);\n'
         '        et.setText(a.name);\n')
b_new = ''
assert raw.count(a_old) == 1, raw.count(a_old)
assert raw.count(b_old) == 1, raw.count(b_old)
raw = raw.replace(a_old, a_new).replace(b_old, b_new)
lines = raw.split("\n")

# 2) dedent the inserted blocks by 8 spaces
starts = []
for i, l in enumerate(lines):
    if l.rstrip().endswith("dlgCard();") and l.startswith(" " * 12):
        body = l.strip()
        ind = len(l) - len(l.lstrip())
        # only blocks we inserted: at least 16 spaces and follow a blank/known context
        if ind >= 16:
            starts.append(i)

ranges = []
for i in starts:
    for j in range(i, len(lines)):
        if "h[0] = showCard(c);" in lines[j]:
            ranges.append((i, j))
            break
print("ranges", ranges)
ded = 0
for (i, j) in ranges:
    for k in range(i, min(j + 1, len(lines))):
        if lines[k].startswith(" " * 8):
            lines[k] = lines[k][8:]
            ded += 1
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("dedented", ded)
