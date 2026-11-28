# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
n = 0
def rep(old, new, cnt=1):
    global s, n
    assert s.count(old) == cnt, (s.count(old), old[:80])
    s = s.replace(old, new)
    n += 1

# ---- 1) 字段：page* 改成 View（包一层 ScrollView），新增按钮字段 ----
rep('    private LinearLayout host, pageHome, pageTask, pageAcc, pageSet;',
    '    private LinearLayout host;\n    private View pageHome, pageTask, pageAcc, pageSet;')
rep('    private TextView tabHome, tabTask, tabAcc, tabSet;',
    '    private TextView tabHome, tabTask, tabAcc, tabSet;\n    private Button btnLock, btnShot, btnNight;')

# ---- 2) buildUi：首页/任务/设置包 ScrollView（账号页里有 ListView，自己不包） ----
rep('''        pageHome = buildHome();
        pageTask = buildTask();
        pageAcc = buildAccounts();
        pageSet = buildSettings();''',
    '''        pageHome = wrapScroll(buildHome());
        pageTask = wrapScroll(buildTask());
        pageAcc = buildAccounts();
        pageSet = wrapScroll(buildSettings());''')

rep('''    private LinearLayout.LayoutParams full() {''',
    '''    /** 给整页套一层滚动容器：内容比屏幕高时可以滑，不会出现「下面那截永远看不见」。 */
    private ScrollView wrapScroll(View inner) {
        ScrollView sv = new ScrollView(this);
        sv.setFillViewport(true);
        sv.setVerticalScrollBarEnabled(false);
        sv.setOverScrollMode(View.OVER_SCROLL_NEVER);
        sv.setClipToPadding(false);
        sv.addView(inner, new android.widget.FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return sv;
    }

    private LinearLayout.LayoutParams full() {''')

# ---- 3) 底部菜单加图标 ----
rep('''        tabHome = mkTab("首页");
        tabTask = mkTab("任务");
        tabAcc = mkTab("账号");
        tabSet = mkTab("设置");''',
    '''        tabHome = mkTab("首页", R.drawable.ic_home);
        tabTask = mkTab("任务", R.drawable.ic_task);
        tabAcc = mkTab("账号", R.drawable.ic_acc);
        tabSet = mkTab("设置", R.drawable.ic_set);''')

rep('''    private TextView mkTab(String text) {
        TextView t = new TextView(this);
        t.setText(text);
        t.setTextSize(13);
        t.setGravity(Gravity.CENTER);
        t.setPadding(0, dp(8), 0, dp(8));
        return t;
    }''',
    '''    private TextView mkTab(String text, int icon) {
        TextView t = new TextView(this);
        t.setText(text);
        t.setTextSize(10.5f);
        t.setGravity(Gravity.CENTER);
        t.setPadding(0, dp(7), 0, dp(5));
        t.setLineSpacing(0, 1f);
        try {
            android.graphics.drawable.Drawable d = getResources().getDrawable(icon);
            int sz = dp(22);
            d.setBounds(0, 0, sz, sz);
            t.setCompoundDrawables(null, d, null, null);
            t.setCompoundDrawablePadding(dp(3));
        } catch (Throwable ignored) {
        }
        return t;
    }''')

# showPage 里同时给图标上色
rep('''            tabs[i].setTextColor(idx == i ? on : off);
            tabs[i].setTypeface(null, idx == i ? android.graphics.Typeface.BOLD : android.graphics.Typeface.NORMAL);''',
    '''            tabs[i].setTextColor(idx == i ? on : off);
            tabs[i].setTypeface(null, idx == i ? android.graphics.Typeface.BOLD : android.graphics.Typeface.NORMAL);
            if (Build.VERSION.SDK_INT >= 23) {
                tabs[i].setCompoundDrawableTintList(android.content.res.ColorStateList.valueOf(idx == i ? on : off));
            }''')

# ---- 4) rowWithButton 拆出可传按钮的版本 ----
rep('''    private LinearLayout rowWithButton(TextView val, String label, String btnText, View.OnClickListener click) {
        LinearLayout r = new LinearLayout(this);''',
    '''    private LinearLayout rowWithButton(TextView val, String label, String btnText, View.OnClickListener click) {
        return rowWithButtonObj(val, label, mkBtn(btnText, true), click);
    }

    /** 和 rowWithButton 一样，但按钮由调用方给，方便之后改字（开启/关闭）。 */
    private LinearLayout rowWithButtonObj(TextView val, String label, Button b, View.OnClickListener click) {
        LinearLayout r = new LinearLayout(this);''')

rep('''        top.addView(l, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        Button b = mkBtn(btnText, true);
        b.setTextSize(12);''',
    '''        top.addView(l, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        b.setTextSize(12);''')

# ---- 5) refreshSec ----
rep('''    private boolean noShot() {
        return getPreferences(MODE_PRIVATE).getBoolean("noShot", false);
    }''',
    '''    private boolean noShot() {
        return getPreferences(MODE_PRIVATE).getBoolean("noShot", false);
    }

    /** 安全卡片上两行的状态文字 + 按钮文字，状态一变就刷一次。 */
    private void refreshSec() {
        boolean lk = lockOn(), ns = noShot();
        if (rowLockVal != null) rowLockVal.setText(lk ? "已开启：打开 App 要先输密码" : "未开启：打开 App 不需要密码");
        if (btnLock != null) btnLock.setText(lk ? "关闭" : "开启");
        if (rowShotVal != null) rowShotVal.setText(ns ? "已禁止：系统截图和录屏是黑的" : "允许：可以正常截图录屏");
        if (btnShot != null) btnShot.setText(ns ? "关闭" : "开启");
    }''')

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("part1 replacements", n, "len", len(s))