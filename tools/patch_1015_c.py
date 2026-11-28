# -*- coding: utf-8 -*-
import io
p = r'D:/123/4/android/src/com/housamo/authkey/MainActivity.java'
s = io.open(p, encoding='utf-8').read()
n0 = len(s.encode('utf-8'))

# 1) doExtract gate
a1 = u'''    private void doExtract() {
        log("--- 开始提取 ---");'''
assert s.count(a1) == 1, 'a1'
s = s.replace(a1, u'''    private void doExtract() {
        if (!permReady()) { showNoPerm(); return; }
        log("--- 开始提取 ---");''', 1)

# 2) doImportNow gate
a2 = u'''    private void doImportNow(final Account a) {
        log("--- 开始导入：" + a.name + " ---");'''
assert s.count(a2) == 1, 'a2'
s = s.replace(a2, u'''    private void doImportNow(final Account a) {
        if (!permReady()) { showNoPerm(); return; }
        log("--- 开始导入：" + a.name + " ---");''', 1)

# 3) settings perm card hint
a3 = u'''        p.addView(perm, cardParams(0));
        fillDeviceInfo();'''
assert s.count(a3) == 1, 'a3'
s = s.replace(a3, u'''        p.addView(perm, cardParams(0));

        TextView permTip = new TextView(this);
        permTip.setText("没有 root 也没装 Shizuku？点上面「Shizuku 权限」有图文步骤；不想装任何东西，就用电脑 + USB 线，提取和导入都在 Windows 版里做。");
        permTip.setTextSize(11);
        permTip.setTextColor(grayColor);
        permTip.setPadding(dp(4), 0, dp(4), dp(10));
        p.addView(permTip);

        fillDeviceInfo();''', 1)

# 4) version
s = s.replace('static final String CURRENT_VER = "1.0.14";', 'static final String CURRENT_VER = "1.0.15";', 1)
assert 'CURRENT_VER = "1.0.15"' in s

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('ok', n0, '->', len(s.encode('utf-8')))
