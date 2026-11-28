# -*- coding: utf-8 -*-
import io

P = "D:/123/4/android/src/com/housamo/authkey/MainActivity.java"
src = io.open(P, encoding="utf-8").read()
orig = len(src)

def rep(old, new, why):
    global src
    n = src.count(old)
    assert n == 1, "anchor count=%d for %s" % (n, why)
    src = src.replace(old, new, 1)

# ---------- 1. 导出路径按游戏分 ----------
rep('''    private File exportRootFileDefault() {
        return new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "东放Key");
    }''',
'''    private File exportRootFileDefault() {
        return new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "东放Key");
    }

    /** 当前游戏在默认导出根下的目录：东放沿用老路径，其他游戏加一层同名子目录。 */
    private File exportRootGameDir() {
        String sub = game.exportSub();
        return sub.length() == 0 ? exportRootFileDefault() : new File(exportRootFileDefault(), sub);
    }

    /** 相对路径前缀（Download/东放Key[/游戏名]/）。 */
    private String exportRelPrefix() {
        String sub = game.exportSub();
        return Environment.DIRECTORY_DOWNLOADS + "/东放Key/" + (sub.length() == 0 ? "" : sub + "/");
    }

    /** 展示用导出目录（带游戏子目录，末尾有 /）。 */
    private String exportRootLabelFull() {
        String sub = game.exportSub();
        return sub.length() == 0 ? exportRootLabel() : exportRootLabel() + sub + "/";
    }

    /** shell 兜底用的导出目录。 */
    private String exportRootShellDir() {
        String sub = game.exportSub();
        return "/sdcard/Download/东放Key" + (sub.length() == 0 ? "" : "/" + sub);
    }

    /** 自定义导出树里当前游戏用的目录：东放直接用根，其他游戏取/建同名子目录。 */
    private android.net.Uri exportTreeForGame() {
        android.net.Uri tree = exportRootUri();
        if (tree == null) return null;
        String sub = game.exportSub();
        if (sub.length() == 0) return tree;
        try {
            String treeId = android.provider.DocumentsContract.getTreeDocumentId(tree);
            android.net.Uri rootDoc = android.provider.DocumentsContract.buildDocumentUriUsingTree(tree, treeId);
            android.net.Uri child = findChild(rootDoc, sub);
            if (child == null) {
                child = android.provider.DocumentsContract.createDocument(getContentResolver(), rootDoc,
                        "vnd.android.document/directory", sub);
            }
            return child == null ? tree : child;
        } catch (Throwable t) {
            log("[导出] 准备游戏子目录失败：" + t);
            return tree;
        }
    }''', "export path helpers")

rep('''        android.net.Uri tree = exportRootUri();
        if (tree != null) {
            String t = exportToTree(tree, safe, data);
            if (t != null) return exportRootLabel() + "/" + safe + "/AuthKey.txt";
        }
        String rel = Environment.DIRECTORY_DOWNLOADS + "/东放Key/" + safe;
        // 1) 直接写（Android 10 及以下，或已授予「所有文件访问」）
        try {
            File dir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "东放Key/" + safe);''',
'''        android.net.Uri tree = exportTreeForGame();
        if (tree != null) {
            String t = exportToTree(tree, safe, data);
            if (t != null) return exportRootLabelFull() + safe + "/AuthKey.txt";
        }
        String rel = exportRelPrefix() + safe;
        // 1) 直接写（Android 10 及以下，或已授予「所有文件访问」）
        try {
            File dir = new File(exportRootGameDir(), safe);''', "exportKeyFolder tree/rel")

rep('''            Res r = shWithInput("mkdir -p '/sdcard/Download/东放Key/" + safe + "' && cat > '/sdcard/Download/东放Key/"
                    + safe + "/AuthKey.txt'", data, 20000);''',
'''            String sdir = exportRootShellDir() + "/" + safe;
            Res r = shWithInput("mkdir -p '" + sdir + "' && cat > '" + sdir + "/AuthKey.txt'", data, 20000);''', "exportKeyFolder shell")

rep('''            Account a = accounts.get(i);
            if (a.folder == null || a.folder.length() == 0) {
                if (exportedExists(a.name)) {
                    a.folder = "/storage/emulated/0/Download/东放Key/" + safeName(a.name) + "/AuthKey.txt";''',
'''            Account a = accounts.get(i);
            if (!inGame(a)) continue;
            if (a.folder == null || a.folder.length() == 0) {
                if (exportedExists(a.name)) {
                    a.folder = "/storage/emulated/0/" + exportRelPrefix() + safeName(a.name) + "/AuthKey.txt";''', "autoExportMissingInner")

rep('''        try {
            File root = exportRootFileDefault();
            File[] dirs = root.listFiles();''',
'''        try {
            File root = exportRootGameDir();
            File[] dirs = root.listFiles();''', "scan default root")

rep('''                    Account a = new Account(safeName(d.getName()), k);
                    a.note = "来自导出文件夹";
                    a.folder = f.getAbsolutePath();''',
'''                    Account a = new Account(safeName(d.getName()), k);
                    a.game = game.id;
                    a.note = "来自导出文件夹";
                    a.folder = f.getAbsolutePath();''', "scan default game")

rep('''        Uri tree = exportRootUri();
        if (tree != null) {
            android.database.Cursor c = null;
            try {
                String treeId = android.provider.DocumentsContract.getTreeDocumentId(tree);
                c = getContentResolver().query(
                        android.provider.DocumentsContract.buildChildDocumentsUriUsingTree(tree, treeId),''',
'''        Uri tree = exportTreeForGame();
        if (tree != null) {
            android.database.Cursor c = null;
            try {
                String treeId = android.provider.DocumentsContract.getDocumentId(tree);
                c = getContentResolver().query(
                        android.provider.DocumentsContract.buildChildDocumentsUriUsingTree(tree, treeId),''', "scan tree root")

rep('''                    Account a = new Account(safeName(nm), k);
                    a.note = "来自导出文件夹";
                    a.folder = exportRootLabel() + "/" + nm + "/AuthKey.txt";''',
'''                    Account a = new Account(safeName(nm), k);
                    a.game = game.id;
                    a.note = "来自导出文件夹";
                    a.folder = exportRootLabelFull() + nm + "/AuthKey.txt";''', "scan tree game")

# ---------- 2. 新记录带上游戏 ----------
rep('''    private void addAccount(String name, String key, String source) {
        Account a = new Account(name, key);
        a.note = "来源：" + source;''',
'''    private void addAccount(String name, String key, String source) {
        Account a = new Account(name, key);
        a.game = game.id;
        a.note = "来源：" + source;''', "addAccount game")

rep('''                        final Account bak = new Account("导入前备份 " + stamp(), old);
                        bak.kind = "backup";''',
'''                        final Account bak = new Account("导入前备份 " + stamp(), old);
                        bak.kind = "backup";
                        bak.game = game.id;''', "backup game")

rep('''        String msg = "即将把「" + a.name + "」（指纹 " + a.fpShort() + "）写进游戏，会先强制停止游戏。\\n\\n"''',
'''        String msg = "即将把「" + a.name + "」（指纹 " + a.fpShort() + "）写进「" + game.label + "」，会先强制停止这个游戏。\\n\\n"''', "import msg")

# ---------- 3. 启动核对 ----------
rep('''    private void refreshCurrentFp() {
        if (curFpBusy) return;
        curFpBusy = true;
        pool.execute(new Runnable() {
            public void run() {
                String fp = null;
                try {
                    String k = null;
                    byte[] d = readKeyAt(EXT_KEY);
                    if (d != null) k = new String(d).trim();
                    if (k == null || k.length() < 8) {
                        byte[] x = readKeyAt(PREFS1);
                        if (x != null) k = extractFromPrefs(new String(x));
                    }
                    if (k != null && k.trim().length() > 20) fp = hash(k.trim()).substring(0, 16);
                } catch (Throwable ignored) {
                }
                final String f = fp;
                runOnUiThread(new Runnable() {
                    public void run() {
                        curFpBusy = false;
                        curFpLoaded = true;
                        curFp = f;
                        refreshAccountsView();
                        if (pendingImport != null && selected() == pendingImport) {
                            pendingImport = null;
                            doImport();
                        }
                    }
                });
            }
        });
    }''',
'''    private void refreshCurrentFp() {
        if (curFpBusy) return;
        curFpBusy = true;
        final String forGame = game.id;
        pool.execute(new Runnable() {
            public void run() {
                String fp = null;
                String key = null;
                try {
                    String k = null;
                    byte[] d = readKeyAt(EXT_KEY);
                    if (d != null) k = new String(d).trim();
                    if (k == null || k.length() < 8) {
                        byte[] x = readKeyAt(PREFS1);
                        if (x != null) k = extractFromPrefs(new String(x));
                    }
                    if (k != null && k.trim().length() > 20) {
                        key = k.trim();
                        fp = hash(key).substring(0, 16);
                    }
                } catch (Throwable ignored) {
                }
                final String f = fp;
                final String kk = key;
                runOnUiThread(new Runnable() {
                    public void run() {
                        curFpBusy = false;
                        curFpLoaded = true;
                        if (!forGame.equals(game.id)) return;
                        curFp = f;
                        curKey = kk;
                        refreshAccountsView();
                        refreshKeyCheckBanner();
                        if (pendingImport != null && selected() == pendingImport) {
                            pendingImport = null;
                            doImport();
                        }
                    }
                });
            }
        });
    }

    private boolean gameInstalled(Game g) {
        try {
            getPackageManager().getPackageInfo(g.pkg, 0);
            return true;
        } catch (Throwable ignored) {
        }
        return new File("/sdcard/Android/data/" + g.pkg).exists();
    }

    /** 游戏里的 key 不在账号库里 → 在任务页顶部提示一次（只提示，用户点了才存）。 */
    private void refreshKeyCheckBanner() {
        if (bannerBox == null) return;
        bannerBox.removeAllViews();
        String k = curKey == null ? "" : curKey.trim();
        if (k.length() < 8 || curFp == null) {
            bannerBox.setVisibility(android.view.View.GONE);
            return;
        }
        Account latest = null;
        boolean known = false;
        for (int i = accounts.size() - 1; i >= 0; i--) {
            Account a = accounts.get(i);
            if (!inGame(a)) continue;
            if (latest == null && !a.isBackup()) latest = a;
            if (a.key != null && a.key.trim().equals(k)) {
                known = true;
                break;
            }
        }
        if (known || curFp.equals(bannerDismissedFp)) {
            bannerBox.setVisibility(android.view.View.GONE);
            return;
        }
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setBackground(roundRect(Color.parseColor("#FFF8E6"), 16, Color.parseColor("#F0D9A8"), 1));
        c.setPadding(dp(14), dp(12), dp(14), dp(12));
        TextView t = new TextView(this);
        t.setText("游戏里的 key 和账号库对不上");
        t.setTextSize(15);
        t.setTextColor(Color.parseColor("#8A6D1F"));
        t.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        c.addView(t);
        TextView d = new TextView(this);
        String msg = "「" + game.label + "」现在用的指纹是 " + curFp + "，账号库里没有这个 key。";
        if (latest != null) msg += "\\n库里最新的是「" + latest.name + "」（" + latest.fpShort() + "）。";
        msg += "\\n想留一份，就点「存到账号库」。";
        d.setText(msg);
        d.setTextSize(12);
        d.setTextColor(Color.parseColor("#7A6633"));
        d.setPadding(0, dp(4), 0, dp(8));
        c.addView(d);
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        Button save = mkBtn("存到账号库", true);
        save.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { saveCurKeyAsSnapshot(); }
        });
        Button skip = mkBtn("不用管", false);
        skip.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                bannerDismissedFp = curFp;
                refreshKeyCheckBanner();
            }
        });
        row.addView(save, new LinearLayout.LayoutParams(0, android.view.ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, android.view.ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        lp.setMargins(dp(8), 0, 0, 0);
        row.addView(skip, lp);
        c.addView(row);
        bannerBox.addView(c);
        bannerBox.setVisibility(android.view.View.VISIBLE);
    }

    private void saveCurKeyAsSnapshot() {
        String k = curKey == null ? "" : curKey.trim();
        if (k.length() < 8) {
            toast("还没读到游戏里的 key");
            return;
        }
        addAccount("游戏内快照 " + stamp(), k, "启动核对：游戏里的 key 不在账号库");
        bannerDismissedFp = curFp;
        refreshKeyCheckBanner();
        log("[快照] 已把「" + game.label + "」当前的 key 存进账号库（指纹 " + curFp + "）");
    }

    /** 两个游戏的分段按钮（任务页与账号页各一张）。 */
    private LinearLayout gameSwitcherCard(boolean withHint) {
        LinearLayout c = card();
        TextView t = new TextView(this);
        t.setText("游戏");
        t.setTextSize(14);
        t.setTextColor(Color.parseColor("#1B1F24"));
        t.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        c.addView(t);
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, dp(8), 0, 0);
        for (int i = 0; i < GAMES.length; i++) {
            final Game g = GAMES[i];
            Button b = mkBtn(g.label, false);
            b.setTag(g.id);
            b.setOnClickListener(new View.OnClickListener() {
                public void onClick(View v) { switchGame(g); }
            });
            LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(0, android.view.ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
            if (i > 0) lp.setMargins(dp(8), 0, 0, 0);
            row.addView(b, lp);
            gameButtons.add(b);
        }
        c.addView(row);
        if (withHint) {
            TextView h = new TextView(this);
            h.setText("两个游戏的账号、备份和导出文件夹都是分开的，切换不会影响另一边。");
            h.setTextSize(11);
            h.setTextColor(Color.parseColor("#9AA3B0"));
            h.setPadding(dp(2), dp(6), 0, 0);
            c.addView(h);
        }
        return c;
    }

    private void styleGameBtns() {
        for (Button b : gameButtons) {
            if (b == null) continue;
            String id = String.valueOf(b.getTag());
            styleSeg(b, game.id.equals(id));
            boolean inst = gameInstalled(gameById(id));
            b.setAlpha(inst ? 1f : 0.55f);
        }
    }

    private void switchGame(Game g) {
        if (g == null || g.id.equals(game.id)) return;
        applyGame(g);
        getPreferences(MODE_PRIVATE).edit().putString("gameId", g.id).apply();
        exportEntries.clear();
        if (list != null) list.clearChoices();
        curFp = null;
        curKey = null;
        curFpLoaded = false;
        bannerDismissedFp = null;
        log("[游戏] 已切换到 " + g.label + "（" + g.pkg + "）");
        toast("已切换到 " + g.label);
        refreshAccountsView();
        updateState();
        refreshCurrentFp();
        syncFromExportFolderAsync();
        fillDeviceInfo();
        if (rowExportVal != null) rowExportVal.setText(exportRootLabelFull());
    }''', "banner + switcher")

# ---------- 4. UI 插入 ----------
rep('''        sub.setPadding(dp(2), 0, 0, dp(8));
        p.addView(sub);

        LinearLayout cur = card();''',
'''        sub.setPadding(dp(2), 0, 0, dp(8));
        p.addView(sub);
        p.addView(gameSwitcherCard(true), cardParams(0));

        bannerBox = new LinearLayout(this);
        bannerBox.setOrientation(LinearLayout.VERTICAL);
        bannerBox.setVisibility(android.view.View.GONE);
        p.addView(bannerBox);

        LinearLayout cur = card();''', "buildTask insert")

rep('''        tvState.setPadding(dp(2), 0, 0, dp(8));
        p.addView(tvState);''',
'''        tvState.setPadding(dp(2), 0, 0, dp(8));
        p.addView(tvState);
        p.addView(gameSwitcherCard(false), cardParams(0));''', "buildAccounts insert")

# ---------- 5. onResume 核对 ----------
rep('''    protected void onResume() {
        super.onResume();
        if (pendingApk != null''',
'''    protected void onResume() {
        super.onResume();
        // 每次回到 App 核对一次：游戏里的 key 变了吗
        if (list != null) curFpLoaded = false;
        refreshCurrentFp();
        if (pendingApk != null''', "onResume")

# ---------- 6. 版本号 ----------
rep('''static final String CURRENT_VER = "1.0.12";''', '''static final String CURRENT_VER = "1.0.13";''', "CURRENT_VER")

io.open(P, "w", encoding="utf-8").write(src)
print("part B ok", orig, "->", len(src))

# --- 清单 & 构建脚本 ---
M = "D:/123/4/android/AndroidManifest.xml"
m = io.open(M, encoding="utf-8").read()
assert 'android:versionCode="13"' in m and 'android:versionName="1.0.12"' in m
m = m.replace('android:versionCode="13"', 'android:versionCode="14"').replace('android:versionName="1.0.12"', 'android:versionName="1.0.13"')
assert "jp.co.lifewonders.liveahero" not in m
old_q = '''        <package android:name="jp.co.lifewonders.housamo" />'''
assert m.count(old_q) == 1
m = m.replace(old_q, old_q + '''
        <package android:name="jp.co.lifewonders.liveahero" />''')
io.open(M, "w", encoding="utf-8").write(m)
print("manifest ok")

B = "D:/123/4/android/build_apk.py"
b = io.open(B, encoding="utf-8").read()
assert 'VERSION_CODE = "13"' in b and 'VERSION_NAME = "1.0.12"' in b, "build ver anchor"
b = b.replace('VERSION_CODE = "13"', 'VERSION_CODE = "14"').replace('VERSION_NAME = "1.0.12"', 'VERSION_NAME = "1.0.13"')
io.open(B, "w", encoding="utf-8").write(b)
print("build_apk ok")
