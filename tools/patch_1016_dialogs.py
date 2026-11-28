# -*- coding: utf-8 -*-
import io
p = r'D:/123/4/android/src/com/housamo/authkey/MainActivity.java'
s = io.open(p, encoding='utf-8').read()

start = s.find(u'    /** 真正要读写游戏目录、但一点权限都没有时的统一提示。 */')
end = s.find(u'    private void copyText(String s) {')
assert start > 0 and end > start, (start, end)
newblock = u'''    // ---------- 好看点的弹窗 ----------

    private LinearLayout dlgCard() {
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setBackground(roundRect(Color.WHITE, 20, 0, 0));
        c.setPadding(dp(20), dp(20), dp(20), dp(14));
        return c;
    }

    private void dlgTitle(LinearLayout c, String title) {
        TextView t = new TextView(this);
        t.setText(title);
        t.setTextSize(17);
        t.setTextColor(Color.parseColor("#101418"));
        t.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        c.addView(t);
    }

    private void dlgSub(LinearLayout c, String text) {
        TextView t = new TextView(this);
        t.setText(text);
        t.setTextSize(12.5f);
        t.setTextColor(Color.parseColor("#6B7280"));
        t.setLineSpacing(dp(4), 1.0f);
        t.setPadding(0, dp(8), 0, 0);
        c.addView(t);
    }

    private View dlgStep(int num, String head, String body) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, dp(14), 0, 0);
        TextView n = new TextView(this);
        n.setText(String.valueOf(num));
        n.setTextSize(11);
        n.setGravity(Gravity.CENTER);
        n.setTextColor(Color.WHITE);
        n.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        n.setBackground(roundRect(Color.parseColor("#2F6BFF"), 11, 0, 0));
        LinearLayout.LayoutParams np = new LinearLayout.LayoutParams(dp(22), dp(22));
        np.rightMargin = dp(10);
        row.addView(n, np);
        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        TextView h = new TextView(this);
        h.setText(head);
        h.setTextSize(13.5f);
        h.setTextColor(Color.parseColor("#101418"));
        h.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        col.addView(h);
        TextView b = new TextView(this);
        b.setText(body);
        b.setTextSize(12.5f);
        b.setTextColor(Color.parseColor("#6B7280"));
        b.setLineSpacing(dp(3), 1.0f);
        b.setPadding(0, dp(3), 0, 0);
        col.addView(b);
        row.addView(col, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0f));
        return row;
    }

    private View dlgOption(String title, String desc, View.OnClickListener click) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setBackground(roundRect(Color.parseColor("#F5F7FB"), 14, Color.parseColor("#E7EBF2"), 1));
        box.setPadding(dp(14), dp(12), dp(14), dp(12));
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        bp.topMargin = dp(10);
        box.setLayoutParams(bp);
        TextView t = new TextView(this);
        t.setText(title);
        t.setTextSize(13.5f);
        t.setTextColor(Color.parseColor("#101418"));
        t.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        box.addView(t);
        TextView d = new TextView(this);
        d.setText(desc);
        d.setTextSize(12.5f);
        d.setTextColor(Color.parseColor("#6B7280"));
        d.setLineSpacing(dp(3), 1.0f);
        d.setPadding(0, dp(4), 0, dp(8));
        box.addView(d);
        TextView go = new TextView(this);
        go.setText("怎么弄  →");
        go.setTextSize(12.5f);
        go.setTextColor(Color.parseColor("#2F6BFF"));
        go.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        box.addView(go);
        box.setOnClickListener(click);
        return box;
    }

    private Button dlgPrimary(String text, View.OnClickListener click) {
        Button b = mkBtn(text, true);
        b.setTextSize(14);
        b.setTextColor(Color.WHITE);
        b.setOnClickListener(click);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(46));
        p.topMargin = dp(16);
        b.setLayoutParams(p);
        return b;
    }

    private Button dlgGhost(String text, View.OnClickListener click, boolean blue) {
        Button b = new Button(this);
        b.setText(text);
        b.setAllCaps(false);
        b.setTextSize(13);
        b.setTextColor(Color.parseColor(blue ? "#2F6BFF" : "#6B7280"));
        b.setBackground(roundRect(Color.TRANSPARENT, 10, 0, 0));
        b.setStateListAnimator(null);
        b.setElevation(0);
        b.setMinHeight(dp(40));
        b.setMinWidth(0);
        b.setPadding(0, 0, 0, 0);
        if (click != null) b.setOnClickListener(click);
        return b;
    }

    private TextView dlgCode(String code) {
        TextView t = new TextView(this);
        t.setText(code);
        t.setTextSize(11.5f);
        t.setTypeface(android.graphics.Typeface.MONOSPACE);
        t.setTextColor(Color.parseColor("#3B4252"));
        t.setBackground(roundRect(Color.parseColor("#F2F4F8"), 10, 0, 0));
        t.setPadding(dp(12), dp(10), dp(12), dp(10));
        t.setTextIsSelectable(true);
        t.setLineSpacing(dp(2), 1.0f);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        p.topMargin = dp(10);
        t.setLayoutParams(p);
        return t;
    }

    private AlertDialog showCard(LinearLayout card) {
        ScrollView sv = new ScrollView(this);
        sv.setVerticalScrollBarEnabled(false);
        sv.setClipToPadding(false);
        sv.addView(card, new android.widget.FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        AlertDialog d = new AlertDialog.Builder(this).setView(sv).create();
        d.show();
        android.view.Window w = d.getWindow();
        if (w != null) {
            w.setBackgroundDrawable(new android.graphics.drawable.ColorDrawable(Color.TRANSPARENT));
            int width = (int) (getResources().getDisplayMetrics().widthPixels * 0.90f);
            w.setLayout(width, ViewGroup.LayoutParams.WRAP_CONTENT);
        }
        return d;
    }

    /** 真正要读写游戏目录、但一点权限都没有时的统一提示。 */
    private void showNoPerm() {
        log("[权限] 既没有 root 也没有 Shizuku，读不到游戏的数据目录。");
        LinearLayout c = dlgCard();
        dlgTitle(c, "还差一步读写权限");
        dlgSub(c, "Android 11 以后，普通 App 读不到游戏的数据目录。下面两种方式任选一种，弄好之后回来点提取就行。");
        c.addView(dlgOption("① 装 Shizuku（免 root，推荐）",
                "手机上下载一个 Shizuku，用开发者选项里的「无线调试」启动一次；不用电脑，手机重启后重新启动一次即可。",
                new View.OnClickListener() {
                    public void onClick(View v) { showShizukuGuide(); }
                }));
        c.addView(dlgOption("② 用电脑 + USB 线",
                "不想装东西就把手机插到电脑上，用 Windows 版一次性搞定，提取和导入都在电脑那边做。",
                new View.OnClickListener() {
                    public void onClick(View v) { showPcGuide(); }
                }));
        showCard(c);
    }

    /** Shizuku 从装到授权的完整步骤。 */
    private void showShizukuGuide() {
        LinearLayout c = dlgCard();
        dlgTitle(c, "用 Shizuku 免 root 开权限");
        dlgSub(c, "Shizuku 把 adb 权限借给本 App，没有 root 也能读写游戏目录。全程约 2 分钟；手机重启后要重新启动一次 Shizuku。");
        c.addView(dlgStep(1, "装 Shizuku", "点下面的「去下载」，装好先别急着打开。"));
        c.addView(dlgStep(2, "打开开发者选项", "设置 → 关于手机 → 连点「版本号」7 次。小米 / Redmi：设置 → 我的设备 → 全部参数与信息 → 连点「OS 版本」7 次。"));
        c.addView(dlgStep(3, "开 USB 调试和无线调试", "设置 → 更多设置（或「系统」）→ 开发者选项 → 打开「USB 调试」和「无线调试」。"));
        c.addView(dlgStep(4, "在 Shizuku 里启动服务", "打开 Shizuku → 点「通过无线调试启动」→ 点「配对」→ 在系统的「无线调试」页点「使用配对码配对设备」，把配对码和端口填进 Shizuku → 回到 Shizuku 点「启动」。"));
        c.addView(dlgStep(5, "回来授权", "回到本 App，点「我已经弄好了，检查一次」，或在设置页点「Shizuku 权限」并允许。授权成功后引导卡会自动消失。"));
        final AlertDialog[] holder = new AlertDialog[1];
        c.addView(dlgPrimary("去下载 Shizuku", new View.OnClickListener() {
            public void onClick(View v) { openUrl("https://github.com/RikkaApps/Shizuku/releases/latest"); }
        }));
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, dp(6), 0, 0);
        row.addView(dlgGhost("打开 Shizuku", new View.OnClickListener() {
            public void onClick(View v) {
                Intent i = getPackageManager().getLaunchIntentForPackage("moe.shizuku.privileged.api");
                if (i != null) startActivity(i);
                else openUrl("https://github.com/RikkaApps/Shizuku/releases/latest");
            }
        }, true), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0f));
        row.addView(dlgGhost("知道了", new View.OnClickListener() {
            public void onClick(View v) { if (holder[0] != null) holder[0].dismiss(); }
        }, false), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0f));
        c.addView(row);
        holder[0] = showCard(c);
    }

    /** 不想装 Shizuku 时，用电脑版的做法。 */
    private void showPcGuide() {
        final String pull = "adb pull /sdcard/Android/data/" + PKG + "/" + game.sub + "/" + game.file;
        LinearLayout c = dlgCard();
        dlgTitle(c, "用电脑（Windows）提取 / 导入");
        dlgSub(c, "不用给手机任何权限：数据线连电脑，全程在电脑上做。");
        c.addView(dlgStep(1, "手机打开 USB 调试", "设置 → 开发者选项 → 打开「USB 调试」，插上数据线，手机上弹窗点「允许调试」。"));
        c.addView(dlgStep(2, "电脑打开项目主页", "下载 Release 里的 AuthKeyManager-win64.zip，解压后运行 AuthKeyManager.exe。"));
        c.addView(dlgStep(3, "在电脑版点「提取」", "key 会存到电脑上，手机 Download/东放Key/" + game.exportSub() + "/ 里也会留一份。"));
        c.addView(dlgStep(4, "要换号就在电脑版点「导入」", "写文件由电脑那边完成，手机不需要 root 或 Shizuku。"));
        TextView codeHint = new TextView(this);
        codeHint.setText("习惯命令行的话，这条命令可以直接拿出来：");
        codeHint.setTextSize(12.5f);
        codeHint.setTextColor(Color.parseColor("#6B7280"));
        codeHint.setPadding(0, dp(16), 0, 0);
        c.addView(codeHint);
        c.addView(dlgCode(pull));
        final AlertDialog[] holder = new AlertDialog[1];
        c.addView(dlgPrimary("复制 adb 命令", new View.OnClickListener() {
            public void onClick(View v) {
                copyText(pull);
                toast("命令已复制");
                if (holder[0] != null) holder[0].dismiss();
            }
        }));
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, dp(6), 0, 0);
        row.addView(dlgGhost("打开项目主页", new View.OnClickListener() {
            public void onClick(View v) { openUrl("https://github.com/fenghuo6183/HousamoAuthKeyManager"); }
        }, true), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0f));
        row.addView(dlgGhost("知道了", new View.OnClickListener() {
            public void onClick(View v) { if (holder[0] != null) holder[0].dismiss(); }
        }, false), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0f));
        c.addView(row);
        holder[0] = showCard(c);
    }

'''
s = s[:start] + newblock + s[end:]

u0 = s.find(u'    private void showUpdatePrompt(final String ver, final String apkUrl) {')
u1 = s.find(u'    private void downloadUpdate(final String ver, final String apkUrl) {')
assert u0 > 0 and u1 > u0, (u0, u1)
newupd = u'''    private void showUpdatePrompt(final String ver, final String apkUrl) {
        promptedUpdate = ver;
        try {
            LinearLayout c = dlgCard();
            dlgTitle(c, "发现新版本 " + ver);
            dlgSub(c, "当前是 " + CURRENT_VER + "。可以直接在这里下载覆盖安装，账号库和导出文件夹里的 key 都不会动。");
            c.addView(dlgStep(1, "点下面的「立即更新」", "安装包在 App 内下载，进度会显示在弹窗里。"));
            c.addView(dlgStep(2, "系统问「是否安装」时点允许", "如果提示「禁止安装未知应用」，会先带你去开那个开关，回来自动继续。"));
            c.addView(dlgStep(3, "装好直接打开", "账号、备份、导出路径都还在原地。"));
            final AlertDialog[] holder = new AlertDialog[1];
            c.addView(dlgPrimary("立即更新", new View.OnClickListener() {
                public void onClick(View v) {
                    if (holder[0] != null) holder[0].dismiss();
                    downloadUpdate(ver, apkUrl);
                }
            }));
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setPadding(0, dp(6), 0, 0);
            row.addView(dlgGhost("去网页下载", new View.OnClickListener() {
                public void onClick(View v) { openUrl(apkUrl); }
            }, true), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0f));
            row.addView(dlgGhost("稍后再说", new View.OnClickListener() {
                public void onClick(View v) { if (holder[0] != null) holder[0].dismiss(); }
            }, false), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0f));
            c.addView(row);
            holder[0] = showCard(c);
        } catch (Throwable t) {
            log("[更新] 弹窗失败：" + t);
        }
    }

'''
s = s[:u0] + newupd + s[u1:]

s = s.replace('static final String CURRENT_VER = "1.0.15";', 'static final String CURRENT_VER = "1.0.16";', 1)
assert 'CURRENT_VER = "1.0.16"' in s

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('dialog rewrite ok', len(s.encode('utf-8')))
