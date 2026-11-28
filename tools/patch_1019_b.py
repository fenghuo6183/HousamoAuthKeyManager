# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
n = 0
def rep(old, new, cnt=1):
    global s, n
    assert s.count(old) == cnt, (s.count(old), old[:90])
    s = s.replace(old, new)
    n += 1

# ---------- 权限卡 ----------
old = '''        rowPermVal = value(0, "检查中…");
        perm.addView(rowWith(rowPermVal, "Shizuku 权限", new View.OnClickListener() {
            public void onClick(View v) { askShizuku(); }
        }));
        perm.addView(divider());
        perm.addView(rowWith(value(0, "点此设置"), "存储权限", new View.OnClickListener() {
            public void onClick(View v) { askStorage(); }
        }));
        perm.addView(divider());
        perm.addView(rowWith(value(0, "刷新"), "重新检测", new View.OnClickListener() {
            public void onClick(View v) {
                pool.execute(new Runnable() {
                    public void run() {
                        hasRoot = checkRoot();
                        rootChecked = true;
                        runOnUiThread(new Runnable() {
                            public void run() { updateState(); }
                        });
                    }
                });
                updateState();
            }
        }));'''
new = '''        rowPermVal = value(0, "检查中…");
        perm.addView(rowWithButton(rowPermVal, "Shizuku 权限", "授权", new View.OnClickListener() {
            public void onClick(View v) { askShizuku(); }
        }));
        perm.addView(divider());
        perm.addView(rowWithButton(value(0, "提取、导出都靠它"), "存储权限", "去设置", new View.OnClickListener() {
            public void onClick(View v) { askStorage(); }
        }));
        perm.addView(divider());
        perm.addView(rowWithButton(value(0, "改完权限点一下"), "重新检测", "刷新", new View.OnClickListener() {
            public void onClick(View v) {
                pool.execute(new Runnable() {
                    public void run() {
                        hasRoot = checkRoot();
                        rootChecked = true;
                        runOnUiThread(new Runnable() {
                            public void run() { updateState(); }
                        });
                    }
                });
                updateState();
            }
        }));'''
rep(old, new)

# ---------- 外观：深色模式带按钮 ----------
rep('''        rowNightVal = value(0, night() ? "深色" : "浅色");
        look.addView(rowWith(rowNightVal, "深色模式", new View.OnClickListener() {
            public void onClick(View v) { toggleNight(); }
        }));''',
    '''        rowNightVal = value(0, night() ? "当前是深色配色" : "当前是浅色配色");
        btnNight = mkBtn(night() ? "切到浅色" : "切到深色", true);
        look.addView(rowWithButtonObj(rowNightVal, "深色模式", btnNight, new View.OnClickListener() {
            public void onClick(View v) { toggleNight(); }
        }));''')

# ---------- 安全卡：两个开关都改成明确的按钮 ----------
rep('''        rowLockVal = value(0, lockOn() ? "已开启" : "未开启");
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
        }));''',
    '''        rowLockVal = value(0, "");
        btnLock = mkBtn(lockOn() ? "关闭" : "开启", true);
        sec.addView(rowWithButtonObj(rowLockVal, "应用锁", btnLock, new View.OnClickListener() {
            public void onClick(View v) {
                if (!lockOn()) { lockMenu(); return; }
                verifyPinThen(new Runnable() {
                    public void run() {
                        getPreferences(MODE_PRIVATE).edit().remove("lockPin").apply();
                        refreshSec();
                        toast("应用锁已关闭");
                        log("[锁] 已关闭应用锁");
                    }
                });
            }
        }));
        sec.addView(divider());
        rowShotVal = value(0, "");
        btnShot = mkBtn(noShot() ? "关闭" : "开启", true);
        sec.addView(rowWithButtonObj(rowShotVal, "防止截屏", btnShot, new View.OnClickListener() {
            public void onClick(View v) {
                getPreferences(MODE_PRIVATE).edit().putBoolean("noShot", !noShot()).apply();
                applyShotFlag();
                refreshSec();
                toast(noShot() ? "已禁止截屏和录屏" : "已允许截屏和录屏");
                log(noShot() ? "[安全] 已开启防截屏" : "[安全] 已关闭防截屏");
            }
        }));
        refreshSec();''')

# ---------- 锁菜单/设密码后同步按钮文字 ----------
rep('''                            getPreferences(MODE_PRIVATE).edit().remove("lockPin").apply();
                            if (rowLockVal != null) rowLockVal.setText("未开启");
                            toast("应用锁已关闭");''',
    '''                            getPreferences(MODE_PRIVATE).edit().remove("lockPin").apply();
                            refreshSec();
                            toast("应用锁已关闭");''')

rep('''                getPreferences(MODE_PRIVATE).edit().putString("lockPin", pinHash(p)).apply();
                unlocked = true;
                if (rowLockVal != null) rowLockVal.setText("已开启");
                if (h[0] != null) h[0].dismiss();''',
    '''                getPreferences(MODE_PRIVATE).edit().putString("lockPin", pinHash(p)).apply();
                unlocked = true;
                refreshSec();
                if (h[0] != null) h[0].dismiss();''')

# ---------- 版本号 ----------
rep('static final String CURRENT_VER = "1.0.18";', 'static final String CURRENT_VER = "1.0.19";')

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("part2 ok", n, "len", len(s))