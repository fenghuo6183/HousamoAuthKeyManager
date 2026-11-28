# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, ("anchor %d times: %r" % (s.count(old), old[:90]))
    s = s.replace(old, new, cnt)
rep('''        if (req == REQ_TREE_IMPORT) {
            scanFolderForKeys(uri);
            return;
        }''',
    '''        if (req == REQ_TREE_IMPORT) {
            scanFolderForKeys(uri);
            return;
        }
        if (req == REQ_TREE_ZIP) {
            writeZipToTree(uri);
            return;
        }''')
rep('if (req != REQ_TREE && req != REQ_TREE_COPY && req != REQ_TREE_BAK && req != REQ_TREE_IMPORT) return;',
    'if (req != REQ_TREE && req != REQ_TREE_COPY && req != REQ_TREE_BAK && req != REQ_TREE_IMPORT && req != REQ_TREE_ZIP) return;')
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("ok")