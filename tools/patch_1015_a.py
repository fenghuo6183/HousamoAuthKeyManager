# -*- coding: utf-8 -*-
import io
p = r'D:/123/4/android/src/com/housamo/authkey/MainActivity.java'
s = io.open(p, encoding='utf-8').read()
def rep(old, new, tag):
    global s
    assert s.count(old) == 1, tag + ' count=' + str(s.count(old))
    s = s.replace(old, new, 1)
    print('ok', tag)

# 1) 字段
rep(u'''    private LinearLayout bannerBox = null;''',
    u'''    private LinearLayout bannerBox = null;
    private LinearLayout permBox = null;''', 'field')

# 2) 任务页插入引导卡容器
rep(u'''        p.addView(gameSwitcherCard(true), cardParams(0));

        bannerBox = new LinearLayout(this);''',
    u'''        p.addView(gameSwitcherCard(true), cardParams(0));

        permBox = new LinearLayout(this);
        permBox.setOrientation(LinearLayout.VERTICAL);
        permBox.setVisibility(android.view.View.GONE);
        p.addView(permBox);

        bannerBox = new LinearLayout(this);''', 'permBox insert')

# 3) updateState 末尾刷新引导卡
rep(u'''        if (rowSelVal != null) {
            Account a = selected();
            rowSelVal.setText(a == null ? "未选择" : a.name + "  ·  " + a.fp());
            rowSelVal.setTextColor(a == null ? grayColor : okColor);
        }
    }''',
    u'''        if (rowSelVal != null) {
            Account a = selected();
            rowSelVal.setText(a == null ? "未选择" : a.name + "  ·  " + a.fp());
            rowSelVal.setTextColor(a == null ? grayColor : okColor);
        }
        refreshPermGuide();
    }''', 'updateState hook')

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('part1 bytes', len(s.encode('utf-8')))
