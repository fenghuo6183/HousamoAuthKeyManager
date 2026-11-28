# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()

def rep(old, new, cnt=1):
    global s
    assert old in s, old[:90]
    s = s.replace(old, new, cnt)

rep('''            dlgPrimary(c, "知道了", new View.OnClickListener() {
                public void onClick(View v) { dismissCard(v); }
            });
            showCard(c);''',
'''            final AlertDialog[] h = new AlertDialog[1];
            c.addView(dlgPrimary("知道了", new View.OnClickListener() {
                public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
            }));
            h[0] = showCard(c);''')

rep('''        dlgPrimary(c, "全部导入（" + fresh.size() + " 个）", new View.OnClickListener() {
            public void onClick(View v) {
                dismissCard(v);
                importFoundKeys(fresh);
            }
        });
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "取消", new View.OnClickListener() {
            public void onClick(View v) { dismissCard(v); }
        }, false);
        c.addView(row);
        showCard(c);''',
'''        final AlertDialog[] h = new AlertDialog[1];
        c.addView(dlgPrimary("全部导入（" + fresh.size() + " 个）", new View.OnClickListener() {
            public void onClick(View v) {
                if (h[0] != null) h[0].dismiss();
                importFoundKeys(fresh);
            }
        }));
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "取消", new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
        }, false);
        c.addView(row);
        h[0] = showCard(c);''')

rep('''        dlgPrimary(c, "去看看账号", new View.OnClickListener() {
            public void onClick(View v) {
                dismissCard(v);
                showPage(2);
            }
        });
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "先这样", new View.OnClickListener() {
            public void onClick(View v) { dismissCard(v); }
        }, false);
        c.addView(row);
        showCard(c);''',
'''        final AlertDialog[] h = new AlertDialog[1];
        c.addView(dlgPrimary("去看看账号", new View.OnClickListener() {
            public void onClick(View v) {
                if (h[0] != null) h[0].dismiss();
                showPage(2);
            }
        }));
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "先这样", new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
        }, false);
        c.addView(row);
        h[0] = showCard(c);''')

io.open(P, "w", encoding="utf-8").write(s)
print("fixed", len(s))
