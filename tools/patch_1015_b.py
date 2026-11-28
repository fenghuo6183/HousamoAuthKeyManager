# -*- coding: utf-8 -*-
import io
p = r'D:/123/4/android/src/com/housamo/authkey/MainActivity.java'
s = io.open(p, encoding='utf-8').read()
anchor = u'''            log("[Shizuku] 请求授权失败：" + t);
        }
    }

    private void openUrl(String url) {'''
assert s.count(anchor) == 1, 'anchor'
newblock = u'''            log("[Shizuku] 请求授权失败：" + t);
        }
    }

    /** 有没有可用的 shell 权限（root 或 Shizuku）。 */
    private boolean permReady() {
        return hasRoot || shizukuReady();
    }

    /** 没有权限时，任务页顶上那张引导卡（有权限就自动隐藏）。 */
    private void refreshPermGuide() {
        if (permBox == null) return;
        permBox.removeAllViews();
        if (!rootChecked || permReady()) {
            permBox.setVisibility(android.view.View.GONE);
            return;
        }
        LinearLayout c = card();
        TextView t = new TextView(this);
        t.setText("还差一步：读写权限");
        t.setTextSize(15);
        t.setTextColor(Color.parseColor("#101418"));
        t.setTypeface(null, android.graphics.Typeface.BOLD);
        c.addView(t);
        TextView d = new TextView(this);
        d.setText("Android 11 以后，手机不让普通 App 直接读别的 App 的数据目录，所以要先“借”一个 shell 权限。下面两种方式任选一种，弄好之后这张卡会自动消失。");
        d.setTextSize(12);
        d.setTextColor(Color.parseColor("#8A93A0"));
        d.setPadding(dp(2), dp(6), dp(2), dp(2));
        c.addView(d);
        c.addView(permOption("① Shizuku（免 root，推荐）",
                "不用连电脑。装个 Shizuku，用开发者选项里的「无线调试」启动一次就行；手机重启后要重新启动一次。",
                new View.OnClickListener() {
                    public void onClick(View v) { showShizukuGuide(); }
                }));
        c.addView(permOption("② 电脑 + USB 数据线",
                "不想装 Shizuku 就插电脑，用 Windows 版一次性搞定——提取和导入都在电脑上做，手机不用给任何权限。",
                new View.OnClickListener() {
                    public void onClick(View v) { showPcGuide(); }
                }));
        Button re = mkBtn("我已经弄好了，检查一次", false);
        re.setTextSize(13);
        re.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { recheckPerm(); }
        });
        c.addView(re, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        permBox.addView(c);
        permBox.setVisibility(android.view.View.VISIBLE);
    }

    private LinearLayout permOption(String title, String desc, final View.OnClickListener click) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(0, dp(12), 0, 0);
        TextView t = new TextView(this);
        t.setText(title);
        t.setTextSize(13);
        t.setTextColor(Color.parseColor("#101418"));
        t.setTypeface(null, android.graphics.Typeface.BOLD);
        box.addView(t);
        TextView d = new TextView(this);
        d.setText(desc);
        d.setTextSize(12);
        d.setTextColor(Color.parseColor("#8A93A0"));
        d.setPadding(0, dp(3), 0, dp(6));
        box.addView(d);
        Button b = mkBtn("怎么弄", true);
        b.setTextSize(13);
        b.setOnClickListener(click);
        box.addView(b, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        return box;
    }

    /** 用户在别处弄好权限后，回来点一下重新检测。 */
    private void recheckPerm() {
        log("[检测] 重新检查 root / Shizuku …");
        pool.execute(new Runnable() {
            public void run() {
                boolean r = false;
                try { r = checkRoot(); } catch (Throwable ignored) { }
                hasRoot = r;
                final boolean alive = shizukuAlive();
                final boolean gr = alive && shizukuGrantedNow();
                runOnUiThread(new Runnable() {
                    public void run() {
                        rootChecked = true;
                        shizukuBinder = alive;
                        shizukuGranted = gr;
                        log(permReady() ? "[检测] 有权限了，现在可以提取 / 导入了。" : "[检测] 还是没有权限（root 未授权、Shizuku 未连接或未授权）。");
                        updateState();
                        if (permReady()) refreshCurrentFp();
                    }
                });
            }
        });
    }

    /** 真正要读写游戏目录、但一点权限都没有时的统一提示。 */
    private void showNoPerm() {
        log("[权限] 既没有 root 也没有 Shizuku，读不到游戏的数据目录。");
        new AlertDialog.Builder(this)
                .setTitle("现在还没有读写权限")
                .setMessage("Android 11 以后，普通 App 读不到游戏的数据目录，这一步只能靠下面两种方式之一：\\n\\n· Shizuku：手机上装一下就能弄，免 root，推荐\\n· 电脑 + USB 线：用 Windows 版，手机什么都不用装")
                .setPositiveButton("用 Shizuku", new android.content.DialogInterface.OnClickListener() {
                    public void onClick(android.content.DialogInterface d, int w) { showShizukuGuide(); }
                })
                .setNeutralButton("用电脑", new android.content.DialogInterface.OnClickListener() {
                    public void onClick(android.content.DialogInterface d, int w) { showPcGuide(); }
                })
                .setNegativeButton("知道了", null)
                .show();
    }

    /** Shizuku 从装到授权的完整步骤。 */
    private void showShizukuGuide() {
        String steps = "Shizuku 会把 adb 权限借给本 App，没有 root 的手机也能读写游戏目录。全程大概 2 分钟，手机重启后要重新启动一次。\\n\\n"
                + "第 1 步｜装 Shizuku\\n"
                + "点下面「去下载」，装好先别急着打开。\\n\\n"
                + "第 2 步｜打开开发者选项\\n"
                + "设置 → 关于手机 → 连点「版本号」7 次。\\n"
                + "小米 / Redmi：设置 → 我的设备 → 全部参数与信息 → 连点「OS 版本」7 次。\\n\\n"
                + "第 3 步｜开 USB 调试和无线调试\\n"
                + "设置 → 更多设置（或「系统」）→ 开发者选项 → 打开「USB 调试」和「无线调试」。\\n\\n"
                + "第 4 步｜在 Shizuku 里启动服务\\n"
                + "打开 Shizuku → 点「通过无线调试启动」→ 点「配对」→ 在系统的「无线调试」页里点「使用配对码配对设备」，把配对码和端口填进 Shizuku → 回到 Shizuku 点「启动」。\\n\\n"
                + "第 5 步｜回来授权\\n"
                + "回到本 App，点这张卡下面的「我已经弄好了，检查一次」，或在设置页点「Shizuku 权限」，在弹窗里点「允许」。授权成功后这张卡会自动消失。";
        final ScrollView sv = new ScrollView(this);
        TextView tv = new TextView(this);
        tv.setText(steps);
        tv.setTextSize(13);
        tv.setTextColor(Color.parseColor("#40474F"));
        tv.setLineSpacing(dp(3), 1f);
        tv.setPadding(dp(18), dp(10), dp(18), dp(10));
        tv.setTextIsSelectable(true);
        sv.addView(tv);
        new AlertDialog.Builder(this)
                .setTitle("用 Shizuku 免 root 开权限")
                .setView(sv)
                .setPositiveButton("去下载 Shizuku", new android.content.DialogInterface.OnClickListener() {
                    public void onClick(android.content.DialogInterface d, int w) {
                        openUrl("https://github.com/RikkaApps/Shizuku/releases/latest");
                    }
                })
                .setNeutralButton("打开 Shizuku", new android.content.DialogInterface.OnClickListener() {
                    public void onClick(android.content.DialogInterface d, int w) {
                        Intent i = getPackageManager().getLaunchIntentForPackage("moe.shizuku.privileged.api");
                        if (i != null) startActivity(i);
                        else openUrl("https://github.com/RikkaApps/Shizuku/releases/latest");
                    }
                })
                .setNegativeButton("知道了", null)
                .show();
    }

    /** 不想装 Shizuku 时，用电脑版的做法。 */
    private void showPcGuide() {
        final String pull = "adb pull /sdcard/Android/data/" + PKG + "/" + game.sub + "/" + game.file;
        String msg = "不用给手机任何权限：用数据线连电脑，全程在电脑上做。\\n\\n"
                + "1. 手机：设置 → 开发者选项 → 打开「USB 调试」，插上数据线，手机上弹窗点「允许调试」。\\n"
                + "2. 电脑：打开项目主页，下载 Release 里的 AuthKeyManager-win64.zip，解压后运行 AuthKeyManager.exe。\\n"
                + "3. 在电脑版里点「提取当前账号的 key」，key 会存到电脑上，手机 Download/东放Key/" + game.exportSub() + "/ 里也会留一份。\\n"
                + "4. 要换号就在电脑版里挑一个 key 点「导入到游戏」，写文件由电脑那边完成，手机不需要 root 或 Shizuku。\\n\\n"
                + "习惯命令行的话，一条命令也能直接拿出来：\\n" + pull;
        new AlertDialog.Builder(this)
                .setTitle("用电脑（Windows）提取 / 导入")
                .setMessage(msg)
                .setPositiveButton("复制 adb 命令", new android.content.DialogInterface.OnClickListener() {
                    public void onClick(android.content.DialogInterface d, int w) {
                        copyText(pull);
                        toast("命令已复制");
                    }
                })
                .setNeutralButton("打开项目主页", new android.content.DialogInterface.OnClickListener() {
                    public void onClick(android.content.DialogInterface d, int w) {
                        openUrl("https://github.com/fenghuo6183/HousamoAuthKeyManager");
                    }
                })
                .setNegativeButton("知道了", null)
                .show();
    }

    private void copyText(String s) {
        try {
            ClipboardManager cm = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
            cm.setPrimaryClip(android.content.ClipData.newPlainText("AuthKey", s));
        } catch (Throwable ignored) {
        }
    }

    private void openUrl(String url) {'''
s = s.replace(anchor, newblock, 1)
io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('partB bytes', len(s.encode('utf-8')))
