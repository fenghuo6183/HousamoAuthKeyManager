# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
orig = s

def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, ("anchor %d: %r" % (s.count(old), old[:80]))
    s = s.replace(old, new, cnt)

# fields
rep('    private TextView rowKeepVal, rowNightVal, rowLockVal, rowShotVal;',
    '''    private TextView rowKeepVal, rowNightVal, rowLockVal, rowShotVal;
    private boolean unlocked = false;
    private long lastBgAt = 0L;''')

# settings card 安全
rep('''        LinearLayout exp = card();
        exp.addView(caption("存储位置"));''',
    '''        LinearLayout sec = card();
        sec.addView(caption("安全"));
        rowLockVal = value(0, lockOn() ? "已开启" : "未开启");
        sec.addView(rowWith(rowLockVal, "应用锁", new View.OnClickListener() {
            public void onClick(View v) { lockMenu(); }
        }));
        sec.addView(divider());
        rowShotVal = value(0, noShot() ? "已禁止" : "允许");
        sec.addView(rowWith(rowShotVal, "防止截屏", new View.OnClickListener() {
            public void onClick(View v) {
                getPreferences(MODE_PRIVATE).edit().putBoolean("noShot", !noShot()).apply();
                applyShotFlag();
                if (rowShotVal != null) rowShotVal.setText(noShot() ? "已禁止" : "允许");
                toast(noShot() ? "已禁止截屏和录屏" : "已允许截屏");
            }
        }));
        TextView sech = new TextView(this);
        sech.setText("应用锁是 4-6 位数字密码，忘了只能重装 App（账号文件仍在 Download，不会丢）。防止截屏打开后，系统截图和录屏都会是黑的。");
        sech.setTextSize(11);
        sech.setTextColor(c("#9AA3B0"));
        sech.setPadding(dp(2), dp(10), dp(2), dp(2));
        sec.addView(sech);
        p.addView(sec, cardParams(0));

        LinearLayout exp = card();
        exp.addView(caption("存储位置"));''')

# lifecycle: apply shot flag + lock on create/resume/stop
rep('''        root.setBackgroundColor(c("#F2F3F6"));
        applyTheme();''',
    '''        root.setBackgroundColor(c("#F2F3F6"));
        applyTheme();
        applyShotFlag();''')

rep('''    protected void onResume() {
        super.onResume();''',
    '''    protected void onResume() {
        super.onResume();
        if (lockOn() && !unlocked) {
            if (lastBgAt == 0L || System.currentTimeMillis() - lastBgAt > 30000L) {
                host.postDelayed(new Runnable() {
                    public void run() { if (!unlocked) showLockScreen(); }
                }, 120L);
            }
        }''')

rep('''    protected void onStop() {
        super.onStop();''',
    '''    protected void onStop() {
        super.onStop();
        lastBgAt = System.currentTimeMillis();''') if 'protected void onStop()' in s else None

# methods: insert before applyTheme definition
anchor = '    private void applyTheme() {'
methods = '''    private boolean lockOn() {
        return getPreferences(MODE_PRIVATE).getString("lockPin", "").length() > 0;
    }

    private boolean noShot() {
        return getPreferences(MODE_PRIVATE).getBoolean("noShot", false);
    }

    private void applyShotFlag() {
        try {
            if (noShot()) {
                getWindow().setFlags(android.view.WindowManager.LayoutParams.FLAG_SECURE,
                        android.view.WindowManager.LayoutParams.FLAG_SECURE);
            } else {
                getWindow().clearFlags(android.view.WindowManager.LayoutParams.FLAG_SECURE);
            }
        } catch (Throwable ignored) {
        }
    }

    private String pinHash(String pin) {
        return hash("housamo-lock|" + pin + "|v1");
    }

    private void lockMenu() {
        LinearLayout c = dlgCard();
        final AlertDialog[] h = new AlertDialog[1];
        if (!lockOn()) {
            dlgTitle(c, "开启应用锁");
            dlgSub(c, "设一个 4-6 位数字密码。之后每次打开 App（或退到后台超过 30 秒回来）都要先输密码。\\n\\n忘了只能重装 App。");
            c.addView(dlgPrimary("设置密码", new View.OnClickListener() {
                public void onClick(View v) {
                    if (h[0] != null) h[0].dismiss();
                    setLockPin();
                }
            }));
        } else {
            dlgTitle(c, "应用锁已开启");
            dlgSub(c, "要关闭或改密码，先输一次现在的密码。");
            c.addView(dlgMenuItem("修改密码", "换一个新的数字密码", false, new View.OnClickListener() {
                public void onClick(View v) {
                    if (h[0] != null) h[0].dismiss();
                    verifyPinThen(new Runnable() { public void run() { setLockPin(); } });
                }
            }));
            c.addView(dlgMenuItem("关闭应用锁", "以后打开 App 不再要密码", true, new View.OnClickListener() {
                public void onClick(View v) {
                    if (h[0] != null) h[0].dismiss();
                    verifyPinThen(new Runnable() {
                        public void run() {
                            getPreferences(MODE_PRIVATE).edit().remove("lockPin").apply();
                            if (rowLockVal != null) rowLockVal.setText("未开启");
                            toast("应用锁已关闭");
                        }
                    });
                }
            }));
        }
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "取消", new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
        }, false);
        c.addView(row);
        h[0] = showCard(c);
    }

    private void setLockPin() {
        LinearLayout c = dlgCard();
        dlgTitle(c, "设置数字密码");
        dlgSub(c, "4-6 位数字。只保存在这台手机上。");
        final EditText et = dlgInput("");
        et.setInputType(android.text.InputType.TYPE_CLASS_NUMBER | android.text.InputType.TYPE_NUMBER_VARIATION_PASSWORD);
        c.addView(et);
        final AlertDialog[] h = new AlertDialog[1];
        c.addView(dlgPrimary("保存", new View.OnClickListener() {
            public void onClick(View v) {
                String p = et.getText().toString().trim();
                if (p.length() < 4 || p.length() > 6) { toast("密码要 4-6 位数字"); return; }
                getPreferences(MODE_PRIVATE).edit().putString("lockPin", pinHash(p)).apply();
                unlocked = true;
                if (rowLockVal != null) rowLockVal.setText("已开启");
                if (h[0] != null) h[0].dismiss();
                toast("应用锁已开启");
            }
        }));
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "取消", new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
        }, false);
        c.addView(row);
        h[0] = showCard(c);
    }

    private void verifyPinThen(final Runnable ok) {
        LinearLayout c = dlgCard();
        dlgTitle(c, "输入现在的密码");
        final EditText et = dlgInput("");
        et.setInputType(android.text.InputType.TYPE_CLASS_NUMBER | android.text.InputType.TYPE_NUMBER_VARIATION_PASSWORD);
        c.addView(et);
        final AlertDialog[] h = new AlertDialog[1];
        c.addView(dlgPrimary("确认", new View.OnClickListener() {
            public void onClick(View v) {
                String p = et.getText().toString().trim();
                if (pinHash(p).equals(getPreferences(MODE_PRIVATE).getString("lockPin", ""))) {
                    if (h[0] != null) h[0].dismiss();
                    ok.run();
                } else {
                    toast("密码不对");
                }
            }
        }));
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "取消", new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
        }, false);
        c.addView(row);
        h[0] = showCard(c);
    }

    private void showLockScreen() {
        if (unlocked || isFinishing()) return;
        LinearLayout c = dlgCard();
        dlgTitle(c, "输入密码");
        dlgSub(c, "东放 Key 管家已上锁。");
        final EditText et = dlgInput("");
        et.setHint("4-6 位数字");
        et.setInputType(android.text.InputType.TYPE_CLASS_NUMBER | android.text.InputType.TYPE_NUMBER_VARIATION_PASSWORD);
        c.addView(et);
        final AlertDialog[] h = new AlertDialog[1];
        c.addView(dlgPrimary("解锁", new View.OnClickListener() {
            public void onClick(View v) {
                String p = et.getText().toString().trim();
                if (pinHash(p).equals(getPreferences(MODE_PRIVATE).getString("lockPin", ""))) {
                    unlocked = true;
                    if (h[0] != null) h[0].dismiss();
                    log("[锁] 已解锁");
                } else {
                    toast("密码不对");
                    et.setText("");
                }
            }
        }));
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "忘了密码", new View.OnClickListener() {
            public void onClick(View v) {
                if (h[0] != null) h[0].dismiss();
                LinearLayout d = dlgCard();
                dlgTitle(d, "忘了密码怎么办");
                dlgSub(d, "密码没有后门，本地只存了它的哈希。\\n\\n唯一的办法是卸载重装 App。你的 key 都在 Download/东放Key/ 里，重装后账号库是空的，但可以从文件夹重新导入，不会丢号。");
                final AlertDialog[] h2 = new AlertDialog[1];
                d.addView(dlgPrimary("知道了", new View.OnClickListener() {
                    public void onClick(View v) { if (h2[0] != null) h2[0].dismiss(); }
                }));
                h2[0] = showCard(d);
                h[0] = showCard(c);
            }
        }, false);
        c.addView(row);
        h[0] = showCard(c);
        h[0].setCancelable(false);
        h[0].setCanceledOnTouchOutside(false);
    }

'''
rep(anchor, methods + anchor)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched", len(orig), "->", len(s))