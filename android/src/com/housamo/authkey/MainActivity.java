package com.housamo.authkey;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.provider.MediaStore;
import android.provider.Settings;
import android.text.InputType;
import android.text.method.ScrollingMovementMethod;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.AdapterView;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ListView;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.security.MessageDigest;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {

    /** 一个受支持的游戏：包名 + key 文件在外部数据目录里的位置。 */
    static class Game {
        final String id, label, pkg, sub, file;

        Game(String id, String label, String pkg, String sub, String file) {
            this.id = id;
            this.label = label;
            this.pkg = pkg;
            this.sub = sub;
            this.file = file;
        }

        String extDir() {
            return "/sdcard/Android/data/" + pkg + "/" + sub;
        }

        String extKey() {
            return extDir() + "/" + file;
        }

        /** 导出 / 备份目录里这个游戏用的子文件夹（东放沿用老路径，不加子目录）。 */
        String exportSub() {
            return "housamo".equals(id) ? "" : label;
        }
    }

    static final Game GAME_HOUSAMO = new Game("housamo", "东京放课后", "jp.co.lifewonders.housamo", "files/Data", "AuthKey");
    static final Game GAME_LIVEHERO = new Game("liveahero", "LiveAHero", "jp.co.lifewonders.liveahero", "files/datas", "userKey");
    static final Game[] GAMES = new Game[]{GAME_HOUSAMO, GAME_LIVEHERO};

    /** 当前游戏；切换时下面这组路径会被重写，其余代码不用动。 */
    static Game game = GAME_HOUSAMO;
    static String PKG = GAME_HOUSAMO.pkg;
    static String EXT_DIR = GAME_HOUSAMO.extDir();
    static String EXT_KEY = GAME_HOUSAMO.extKey();
    static String PREFS1 = "/data/data/" + PKG + "/shared_prefs/" + PKG + ".v2.playerprefs.xml";
    static String PREFS2 = "/data/user/0/" + PKG + "/shared_prefs/" + PKG + ".v2.playerprefs.xml";

    static Game gameById(String id) {
        for (Game g : GAMES) if (g.id.equals(id)) return g;
        return GAME_HOUSAMO;
    }
    static final String VAULT = "vault";
    static final String VAULT_KEY = "accounts";
    static final String CURRENT_VER = "1.0.13";
    static final String UP_API = "https://api.github.com/repos/fenghuo6183/HousamoAuthKeyManager/releases/latest";
    private static File pendingApk = null;
    private String promptedUpdate = "";

    private TextView tvState;
    private LinearLayout host, pageHome, pageTask, pageAcc, pageSet;
    private TextView tabHome, tabTask, tabAcc, tabSet;
    private TextView rowRootVal, rowGameVal, rowShzkVal, rowPermVal, rowCount, rowSaved, rowSelVal;
    private TextView rowStoreVal, rowResVal, rowOsVal, rowVerVal;
    private TextView rowSvcVal, rowModeVal, rowBatteryVal, rowNotifVal, rowGameVerVal, rowExportVal, rowUpdateVal;
    private TextView rowBakVal;
    private static final int REQ_TREE = 0x71;
    private static final int REQ_TREE_COPY = 0x72;
    private static final int REQ_TREE_BAK = 0x73;
    private final java.util.List<Account> exportEntries = new java.util.ArrayList<Account>();
    private Account copyTarget = null;
    private boolean copyMove = false;
    private TextView rowBackupVal;
    private TextView tvLog;
    private ScrollView logScroll;
    private ListView list;
    private AccountAdapter adapter;
    private final List<Account> accounts = new ArrayList<Account>();
    private final List<Account> accView = new ArrayList<Account>();
    private int accTab = 0;
    private Button segA, segB, bMain, bRename, bDel;
    private TextView emptyHint, tvAccHint;
    /** 游戏里当前正在用的 key 指纹（后台读，用来在卡片上标「游戏在用」）。 */
    private String curFp = null;
    /** 游戏里当前 key 的原文（启动核对要用）。 */
    private String curKey = null;
    /** 用户在核对卡片上点过「不用管」的那个指纹，不再重复打扰。 */
    private String bannerDismissedFp = null;
    private LinearLayout bannerBox = null;
    private final java.util.List<Button> gameButtons = new java.util.ArrayList<Button>();
    private Account pendingImport = null;
    private boolean curFpBusy = false;
    private boolean curFpLoaded = false;
    private int curPage = 0;
    private final ExecutorService pool = Executors.newSingleThreadExecutor();
    private boolean rootChecked = false;
    private boolean hasRoot = false;
    private boolean shizukuBinder = false;
    private boolean shizukuGranted = false;
    static final int REQ_SHIZUKU = 0x5A1;

    // ---------- Account ----------

    static class Account {
        String name = "";
        String note = "";
        String key = "";
        String created = "";
        String folder = "";
        String kind = "account";
        /** 属于哪个游戏（housamo / liveahero）；空 = 老数据，算作东京放课后。 */
        String game = "housamo";

        Account() {
        }

        Account(String n, String k) {
            name = n;
            key = k;
            created = stamp();
        }

        boolean isBackup() {
            return "backup".equals(kind);
        }

        String fp() {
            if (key.length() <= 20) return "短key(" + key.length() + ")";
            return hash(key).substring(0, 16) + " | " + key.length() + "B";
        }

        String fpShort() {
            if (key.length() <= 20) return "短key";
            return hash(key).substring(0, 16);
        }

        String sizeText() {
            return key.length() + "B";
        }

        JSONObject toJson() throws Exception {
            JSONObject o = new JSONObject();
            o.put("name", name);
            o.put("note", note);
            o.put("key", key);
            o.put("created", created);
            o.put("folder", folder);
            o.put("kind", kind);
            o.put("game", game);
            return o;
        }

        static Account fromJson(JSONObject o) {
            Account a = new Account();
            a.name = o.optString("name", "");
            a.note = o.optString("note", "");
            a.key = o.optString("key", "");
            a.created = o.optString("created", "");
            a.folder = o.optString("folder", "");
            a.kind = o.optString("kind", "");
            a.game = o.optString("game", "housamo");
            if (a.game == null || a.game.length() == 0) a.game = "housamo";
            if (a.kind.length() == 0) a.kind = a.name.startsWith("导入前备份") ? "backup" : "account";
            return a;
        }
    }

    static String stamp() {
        return new SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US).format(new Date());
    }

    static String hash(String s) {
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] d = md.digest(s.getBytes("UTF-8"));
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < 8; i++) sb.append(String.format(Locale.US, "%02x", d[i]));
            return sb.toString();
        } catch (Exception e) {
            return "????";
        }
    }

    /** 切换当前游戏：把静态路径全部指到这个游戏上。 */
    private void applyGame(Game g) {
        if (g == null) g = GAME_HOUSAMO;
        game = g;
        PKG = g.pkg;
        EXT_DIR = g.extDir();
        EXT_KEY = g.extKey();
        PREFS1 = "/data/data/" + g.pkg + "/shared_prefs/" + g.pkg + ".v2.playerprefs.xml";
        PREFS2 = "/data/user/0/" + g.pkg + "/shared_prefs/" + g.pkg + ".v2.playerprefs.xml";
    }

    // ---------- 生命周期 ----------

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        applyGame(gameById(getPreferences(MODE_PRIVATE).getString("gameId", "housamo")));
        setContentView(buildUi());
        loadVault();
        refreshList();
        maybeShowDisclaimer();
        syncFromExportFolderAsync();

        int startPage = getPreferences(MODE_PRIVATE).getInt("page", 0);
        if (getIntent() != null && getIntent().hasExtra("page")) {
            startPage = getIntent().getIntExtra("page", startPage);
        }
        if (startPage >= 0 && startPage <= 3) showPage(startPage);
        pool.execute(new Runnable() {
            public void run() {
              try {
                android.util.Log.i("HSK", "pool started");
                log("[启动] 正在检查权限与游戏状态...");
                final boolean[] rr = new boolean[]{false};
                Thread rt = new Thread(new Runnable() {
                    public void run() {
                        try { rr[0] = checkRoot(); } catch (Throwable ignored) {}
                    }
                });
                rt.start();
                try { rt.join(2500); } catch (InterruptedException ignored) {}
                hasRoot = rr[0];
                rootChecked = true;
                runOnUiThread(new Runnable() {
                    public void run() {
                        updateState();
                    }
                });
                log(hasRoot ? "[root] 已获取 root 权限，可直接读写游戏私有目录。" : "[root] 未获取 root。若已启动 Shizuku，点上方「Shizuku」授权后即可免 root 读写游戏目录。");
                shizukuBinder = shizukuAlive();
                if (shizukuBinder) {
                    shizukuGranted = shizukuGrantedNow();
                    log(shizukuGranted ? "[Shizuku] 已连接并授权：走 shell 通道，无需 root。"
                                       : "[Shizuku] 已连接，尚未授权：点「Shizuku」按钮授权。");
                } else {
                    log("[Shizuku] 未连接（未安装 Shizuku 或服务未启动）。");
                }
                checkUpdate(false);
                String found = findGamePackages();
                log("[游戏] 检测到的相关包名：" + (found.length() == 0 ? "无（确认游戏装在同一台手机上）" : found));
                log("[游戏] 数据目录 " + EXT_DIR + "：" + (new File(EXT_DIR).exists() ? "存在" : "App 无权直接访问（Android 11+ 正常，走 Shizuku/root 通道）"));
                new Thread(new Runnable() {
                    public void run() { autoExportMissing(); }
                }).start();
              } catch (Throwable t) {
                android.util.Log.e("HSK", "pool crash", t);
                log("[启动] 检查出错：" + t);
              }
            }
        });
    }


    @Override
    protected void onNewIntent(android.content.Intent intent) {
        super.onNewIntent(intent);
        if (intent != null) {
            setIntent(intent);
            if (intent.hasExtra("page")) {
                int pg = intent.getIntExtra("page", 0);
                showPage(pg);
                log("[页面] 切换到 " + pg);
            }
        }
        try {
            rikka.shizuku.Shizuku.addRequestPermissionResultListener(
                new rikka.shizuku.Shizuku.OnRequestPermissionResultListener() {
                    public void onRequestPermissionResult(int request, int grantResult) {
                        if (request != REQ_SHIZUKU) return;
                        shizukuGranted = grantResult == PackageManager.PERMISSION_GRANTED;
                        log(shizukuGranted ? "[Shizuku] 授权成功，现在可以免 root 读写游戏数据目录。"
                                           : "[Shizuku] 授权被拒绝。");
                        runOnUiThread(new Runnable() {
                            public void run() {
                                updateState();
                            }
                        });
                    }
                });
        } catch (Throwable ignored) {
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        pool.shutdownNow();
    }

    // ---------- UI ----------

    private int dp(int v) {
        return (int) TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_DIP, v, getResources().getDisplayMetrics());
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.parseColor("#F2F3F6"));

        host = new LinearLayout(this);
        host.setOrientation(LinearLayout.VERTICAL);
        root.addView(host, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        pageHome = buildHome();
        pageTask = buildTask();
        pageAcc = buildAccounts();
        pageSet = buildSettings();
        host.addView(pageHome, full());
        host.addView(pageTask, full());
        host.addView(pageAcc, full());
        host.addView(pageSet, full());

        View line = new View(this);
        line.setBackgroundColor(Color.parseColor("#E6E9EF"));
        root.addView(line, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));

        LinearLayout nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        nav.setBackgroundColor(Color.WHITE);
        nav.setPadding(0, dp(6), 0, dp(6));
        tabHome = mkTab("首页");
        tabTask = mkTab("任务");
        tabAcc = mkTab("账号");
        tabSet = mkTab("设置");
        tabHome.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { showPage(0); }
        });
        tabTask.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { showPage(1); }
        });
        tabAcc.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { showPage(2); }
        });
        tabSet.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { showPage(3); }
        });
        nav.addView(tabHome, weightNav());
        nav.addView(tabTask, weightNav());
        nav.addView(tabAcc, weightNav());
        nav.addView(tabSet, weightNav());
        root.addView(nav, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        showPage(0);
        return root;
    }

    private TextView mkTab(String text) {
        TextView t = new TextView(this);
        t.setText(text);
        t.setTextSize(13);
        t.setGravity(Gravity.CENTER);
        t.setPadding(0, dp(8), 0, dp(8));
        return t;
    }

    private LinearLayout.LayoutParams weightNav() {
        return new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
    }

    private LinearLayout.LayoutParams full() {
        return new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
    }

    private void showPage(int idx) {
        if (pageHome == null) return;
        if (idx < 0 || idx > 3) idx = 0;
        curPage = idx;
        getPreferences(MODE_PRIVATE).edit().putInt("page", idx).apply();
        pageHome.setVisibility(idx == 0 ? View.VISIBLE : View.GONE);
        pageTask.setVisibility(idx == 1 ? View.VISIBLE : View.GONE);
        pageAcc.setVisibility(idx == 2 ? View.VISIBLE : View.GONE);
        pageSet.setVisibility(idx == 3 ? View.VISIBLE : View.GONE);
        int on = Color.parseColor("#2F6BFF");
        int off = Color.parseColor("#9AA3B0");
        TextView[] tabs = new TextView[]{tabHome, tabTask, tabAcc, tabSet};
        for (int i = 0; i < tabs.length; i++) {
            if (tabs[i] == null) continue;
            tabs[i].setTextColor(idx == i ? on : off);
            tabs[i].setTypeface(null, idx == i ? android.graphics.Typeface.BOLD : android.graphics.Typeface.NORMAL);
        }
        if (idx == 2) {
            curFpLoaded = false;
            refreshCurrentFp();
        }
    }

    private LinearLayout page() {
        LinearLayout p = new LinearLayout(this);
        p.setOrientation(LinearLayout.VERTICAL);
        p.setPadding(dp(14), dp(16), dp(14), dp(8));
        return p;
    }

    private TextView pageTitle(String text) {
        TextView t = new TextView(this);
        t.setText(text);
        t.setTextSize(24);
        t.setTextColor(Color.parseColor("#101418"));
        t.setTypeface(null, android.graphics.Typeface.BOLD);
        t.setPadding(dp(2), 0, 0, dp(10));
        return t;
    }

    private LinearLayout buildHome() {
        LinearLayout p = page();
        p.addView(pageTitle("首页"));
        TextView sub = new TextView(this);
        sub.setText("东放账号管家  ·  备份 / 迁移 / 多开");
        sub.setTextSize(12);
        sub.setTextColor(Color.parseColor("#9AA3B0"));
        sub.setPadding(dp(2), 0, 0, dp(8));
        p.addView(sub);

        LinearLayout info = card();
        rowResVal = value(0, "—");
        rowGameVerVal = value(0, "—");
        rowVerVal = value(0, "—");
        rowSvcVal = value(0, "检测中...");
        info.addView(rowWith(rowResVal, "屏幕分辨率", null));
        info.addView(divider());
        info.addView(rowWith(rowGameVerVal, "游戏版本", null));
        info.addView(divider());
        info.addView(rowWith(rowVerVal, "App 版本", null));
        info.addView(divider());
        info.addView(rowWith(rowSvcVal, "服务状态", null));
        p.addView(info, cardParams(0));

        LinearLayout mode = card();
        rowModeVal = value(0, "检测中...");
        mode.addView(rowWith(rowModeVal, "运行模式", null));
        TextView mh = new TextView(this);
        mh.setText("免 root 时走 Shizuku shell，有 root 时优先 root。");
        mh.setTextSize(11);
        mh.setTextColor(Color.parseColor("#9AA3B0"));
        mh.setPadding(dp(2), dp(2), 0, dp(4));
        mode.addView(mh);
        p.addView(mode, cardParams(0));

        LinearLayout perm = card();
        rowShzkVal = value(0, "未连接");
        rowRootVal = value(0, "检测中...");
        rowStoreVal = value(0, "检测中...");
        rowBatteryVal = value(0, "检测中...");
        rowNotifVal = value(0, "检测中...");
        perm.addView(rowWith(rowShzkVal, "Shizuku 权限", new View.OnClickListener() {
            public void onClick(View v) { askShizuku(); }
        }));
        perm.addView(divider());
        perm.addView(rowWith(rowRootVal, "Root 权限", null));
        perm.addView(divider());
        perm.addView(rowWith(rowStoreVal, "外部存储权限", new View.OnClickListener() {
            public void onClick(View v) { askStorage(); }
        }));
        perm.addView(divider());
        perm.addView(rowWith(rowBatteryVal, "电池优化白名单", new View.OnClickListener() {
            public void onClick(View v) { askBattery(); }
        }));
        perm.addView(divider());
        perm.addView(rowWith(rowNotifVal, "通知权限", new View.OnClickListener() {
            public void onClick(View v) { askNotif(); }
        }));
        p.addView(perm, cardParams(0));
        fillDeviceInfo();

        TextView more = new TextView(this);
        more.setText("提取 / 导入 / 导出 / 运行日志 都在「任务」页");
        more.setTextSize(11);
        more.setTextColor(Color.parseColor("#9AA3B0"));
        more.setPadding(dp(4), dp(8), 0, 0);
        p.addView(more);
        return p;
    }

    private LinearLayout buildTask() {
        LinearLayout p = page();
        p.addView(pageTitle("任务"));
        TextView sub = new TextView(this);
        sub.setText("提取 / 复制到其他文件夹 / 日志 都在这里");
        sub.setTextSize(12);
        sub.setTextColor(Color.parseColor("#9AA3B0"));
        sub.setPadding(dp(2), 0, 0, dp(8));
        p.addView(sub);
        p.addView(gameSwitcherCard(true), cardParams(0));

        bannerBox = new LinearLayout(this);
        bannerBox.setOrientation(LinearLayout.VERTICAL);
        bannerBox.setVisibility(android.view.View.GONE);
        p.addView(bannerBox);

        LinearLayout cur = card();
        rowSelVal = value(0, "未选择");
        cur.addView(rowWith(rowSelVal, "当前账号", new View.OnClickListener() {
            public void onClick(View v) { showPage(2); }
        }));
        TextView ch = new TextView(this);
        ch.setText("点这一行去「账号」页挑一个 key，下面两个操作都针对它");
        ch.setTextSize(11);
        ch.setTextColor(Color.parseColor("#9AA3B0"));
        ch.setPadding(dp(2), dp(2), 0, dp(4));
        cur.addView(ch);
        p.addView(cur, cardParams(0));

        p.addView(taskCard("提取当前账号的 key", "把游戏里正在登录的账号 key 抽出来存进账号库，并自动存一份到「设置 → 导出位置」的文件夹。", new View.OnClickListener() {
            public void onClick(View v) { doExtract(); }
        }), cardParams(0));

        p.addView(taskCard("把选中的 key 复制到其他文件夹", "复制一份到你指定的文件夹（备份到别处、发给另一台设备都行）；选「移动」的话，复制完会把原来导出文件夹里的那份删掉。", new View.OnClickListener() {
            public void onClick(View v) { startCopyMove(); }
        }), cardParams(0));

        LinearLayout lg = card();
        lg.addView(caption("运行日志"));
        logScroll = new ScrollView(this);
        tvLog = new TextView(this);
        tvLog.setTextSize(11);
        tvLog.setTextColor(Color.parseColor("#5B6470"));
        tvLog.setTypeface(android.graphics.Typeface.MONOSPACE);
        tvLog.setMovementMethod(new ScrollingMovementMethod());
        logScroll.addView(tvLog);
        lg.addView(logScroll, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        p.addView(lg, cardParams(1));
        return p;
    }

    private LinearLayout taskCard(String title, String desc, View.OnClickListener click) {
        LinearLayout c = card();
        LinearLayout head = new LinearLayout(this);
        head.setOrientation(LinearLayout.HORIZONTAL);
        head.setGravity(Gravity.CENTER_VERTICAL);
        head.setPadding(0, dp(10), 0, dp(4));
        TextView t = new TextView(this);
        t.setText(title);
        t.setTextSize(15);
        t.setTextColor(Color.parseColor("#101418"));
        t.setTypeface(null, android.graphics.Typeface.BOLD);
        Button b = mkBtn("开始", true);
        b.setTextSize(13);
        b.setMinHeight(dp(34));
        b.setMinWidth(dp(68));
        b.setOnClickListener(click);
        head.addView(t, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        head.addView(b);
        c.addView(head);
        TextView d = new TextView(this);
        d.setText(desc);
        d.setTextSize(12);
        d.setTextColor(Color.parseColor("#8A93A0"));
        d.setPadding(dp(2), 0, dp(2), dp(4));
        c.addView(d);
        return c;
    }

    private LinearLayout buildAccounts() {
        if (getIntent() != null && getIntent().hasExtra("accTab")) {
            accTab = getIntent().getIntExtra("accTab", 0) == 1 ? 1 : 0;
        }
        LinearLayout p = page();
        LinearLayout head = new LinearLayout(this);
        head.setOrientation(LinearLayout.HORIZONTAL);
        head.setGravity(Gravity.CENTER_VERTICAL);
        TextView t = pageTitle("账号");
        head.addView(t, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        rowCount = value(0, "0 个");
        head.addView(rowCount);
        p.addView(head);
        tvState = new TextView(this);
        tvState.setTextSize(12);
        tvState.setTextColor(Color.parseColor("#8A93A0"));
        tvState.setPadding(dp(2), 0, 0, dp(8));
        p.addView(tvState);
        p.addView(gameSwitcherCard(false), cardParams(0));

        LinearLayout seg = new LinearLayout(this);
        seg.setOrientation(LinearLayout.HORIZONTAL);
        segA = mkBtn("账号", false);
        segB = mkBtn("备份", false);
        segA.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { switchAccTab(0); }
        });
        segB.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { switchAccTab(1); }
        });
        LinearLayout.LayoutParams s1 = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        LinearLayout.LayoutParams s2 = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        s2.setMargins(dp(8), 0, 0, 0);
        seg.addView(segA, s1);
        seg.addView(segB, s2);
        p.addView(seg, cardParams(0));

        LinearLayout rf = card();
        TextView rfVal = value(0, "账号库 + 导出文件夹");
        rf.addView(rowWith(rfVal, "重新扫描 key", new View.OnClickListener() {
            public void onClick(View v) {
                toast("正在扫描导出文件夹…");
                syncFromExportFolderAsync();
            }
        }));
        p.addView(rf, cardParams(0));

        android.widget.FrameLayout listWrap = new android.widget.FrameLayout(this);
        list = new ListView(this);
        list.setChoiceMode(ListView.CHOICE_MODE_SINGLE);
        list.setDivider(null);
        list.setSelector(roundRect(Color.TRANSPARENT, 0, 0, 0));
        list.setPadding(0, dp(8), 0, dp(8));
        list.setClipToPadding(false);
        list.setBackgroundColor(Color.TRANSPARENT);
        list.setCacheColorHint(Color.TRANSPARENT);
        adapter = new AccountAdapter();
        list.setAdapter(adapter);
        list.setOnItemClickListener(new AdapterView.OnItemClickListener() {
            public void onItemClick(AdapterView<?> parent, View v, int pos, long id) {
                updateState();
            }
        });
        list.setOnItemLongClickListener(new AdapterView.OnItemLongClickListener() {
            public boolean onItemLongClick(AdapterView<?> parent, View v, int pos, long id) {
                list.setItemChecked(pos, true);
                updateState();
                showAccMenu();
                return true;
            }
        });
        listWrap.addView(list, new android.widget.FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        emptyHint = new TextView(this);
        emptyHint.setTextSize(12);
        emptyHint.setTextColor(Color.parseColor("#9AA3B0"));
        emptyHint.setGravity(Gravity.CENTER);
        emptyHint.setPadding(dp(24), dp(10), dp(24), dp(10));
        android.widget.FrameLayout.LayoutParams ep = new android.widget.FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT, Gravity.CENTER);
        listWrap.addView(emptyHint, ep);
        p.addView(listWrap, cardParams(1));

        LinearLayout op = card();
        tvAccHint = new TextView(this);
        tvAccHint.setTextSize(11);
        tvAccHint.setTextColor(Color.parseColor("#9AA3B0"));
        tvAccHint.setPadding(dp(2), dp(8), dp(2), dp(6));
        op.addView(tvAccHint);
        bMain = mkBtn("导入到游戏", true);
        bMain.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { doImport(); }
        });
        op.addView(bMain, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));

        LinearLayout row1 = new LinearLayout(this);
        row1.setOrientation(LinearLayout.HORIZONTAL);
        bRename = mkBtn("重命名", false);
        bRename.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { doRename(); }
        });
        bDel = mkBtn("删除", false);
        bDel.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { doDelete(); }
        });
        row1.addView(bRename, weight());
        row1.addView(bDel, weight());
        op.addView(row1);
        p.addView(op, cardParams(0));
        return p;
    }

    private LinearLayout buildSettings() {
        LinearLayout p = page();
        p.addView(pageTitle("设置"));

        LinearLayout perm = card();
        perm.addView(caption("权限"));
        rowPermVal = value(0, "检查中…");
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
        }));
        p.addView(perm, cardParams(0));

        LinearLayout exp = card();
        exp.addView(caption("存储位置"));
        rowExportVal = value(0, exportRootLabel());
        exp.addView(rowWithButton(rowExportVal, "导出位置", "更改", new View.OnClickListener() {
            public void onClick(View v) { chooseExportDir(); }
        }));
        exp.addView(divider());
        rowBackupVal = value(0, backupRootLabel());
        exp.addView(rowWithButton(rowBackupVal, "备份位置", "更改", new View.OnClickListener() {
            public void onClick(View v) { chooseBackupDir(); }
        }));
        exp.addView(divider());
        exp.addView(rowWith(value(0, "每个 key 一个子文件夹，里面是 AuthKey.txt"), "导出结构", null));
        TextView sh = new TextView(this);
        sh.setText("备份位置是每次导入前，自动把游戏里正在用的 key 存一份的地方。不换就存在 Download/东放Key/导入前备份/。");
        sh.setTextSize(11);
        sh.setTextColor(Color.parseColor("#9AA3B0"));
        sh.setPadding(dp(2), dp(10), dp(2), dp(2));
        exp.addView(sh);
        p.addView(exp, cardParams(0));

        LinearLayout about = card();
        about.addView(caption("关于"));
        String selfVer = "?";
        try {
            android.content.pm.PackageInfo spi = getPackageManager().getPackageInfo(getPackageName(), 0);
            selfVer = (spi.versionName == null ? "?" : spi.versionName) + " (" + spi.versionCode + ")";
        } catch (Throwable ignored) { }
        about.addView(rowWith(value(0, selfVer), "版本", null));
        about.addView(divider());
        rowUpdateVal = value(0, "未检查");
        about.addView(rowWith(rowUpdateVal, "检查更新", new View.OnClickListener() {
            public void onClick(View v) { checkUpdate(true); }
        }));
        about.addView(divider());
        about.addView(rowWith(value(0, "点此打开 ↗"), "项目主页", new View.OnClickListener() {
            public void onClick(View v) {
                openUrl("https://github.com/fenghuo6183/HousamoAuthKeyManager");
            }
        }));
        TextView url = new TextView(this);
        url.setText("github.com/fenghuo6183/HousamoAuthKeyManager");
        url.setTextSize(11);
        url.setTextColor(Color.parseColor("#2F6BFF"));
        url.setPadding(dp(2), dp(2), 0, dp(6));
        url.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                openUrl("https://github.com/fenghuo6183/HousamoAuthKeyManager");
            }
        });
        about.addView(url);
        about.addView(divider());
        about.addView(rowWith(value(0, "MIT"), "开源协议", null));
        TextView note = new TextView(this);
        note.setText("仅做 AuthKey 文件的复制备份，不修改游戏数据、不联网。账号风险自负。");
        note.setTextSize(11);
        note.setTextColor(Color.parseColor("#9AA3B0"));
        note.setPadding(dp(2), dp(10), 0, 0);
        about.addView(note);
        p.addView(about, cardParams(0));

        Button bClear = mkBtn("清空账号库", false);
        bClear.setTextColor(Color.parseColor("#E5484D"));
        bClear.setBackground(roundRect(Color.WHITE, 10, Color.parseColor("#F3B4B6"), 1));
        bClear.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                new AlertDialog.Builder(MainActivity.this)
                        .setTitle("清空账号库")
                        .setMessage("会删除本机保存的所有账号记录（各账号导出到 Download 的 AuthKey.txt 不会删）。")
                        .setPositiveButton("清空", new android.content.DialogInterface.OnClickListener() {
                            public void onClick(android.content.DialogInterface d, int w) {
                                accounts.clear();
                                saveVault();
                                refreshList();
                                log("[库] 已清空账号库");
                            }
                        })
                        .setNegativeButton("取消", null)
                        .show();
            }
        });
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        bp.setMargins(0, dp(8), 0, 0);
        p.addView(bClear, bp);
        return p;
    }

    private class AccountAdapter extends android.widget.BaseAdapter {
        public int getCount() { return accView.size(); }
        public Object getItem(int i) { return accView.get(i); }
        public long getItemId(int i) { return i; }

        public View getView(int pos, View convert, ViewGroup parent) {
            Account a = accView.get(pos);
            boolean on = list != null && list.getCheckedItemPosition() == pos;

            LinearLayout box = new LinearLayout(MainActivity.this);
            box.setOrientation(LinearLayout.HORIZONTAL);
            box.setGravity(Gravity.CENTER_VERTICAL);
            box.setPadding(dp(12), dp(11), dp(10), dp(11));
            box.setBackground(roundRect(on ? Color.parseColor("#F2F6FF") : Color.WHITE,
                    12, on ? Color.parseColor("#AFC7FF") : Color.parseColor("#EBEFF5"), 1));

            LinearLayout col = new LinearLayout(MainActivity.this);
            col.setOrientation(LinearLayout.VERTICAL);

            TextView name = new TextView(MainActivity.this);
            name.setText(a.isBackup() ? a.name.replace("导入前备份", "备份") : a.name);
            name.setTextSize(15);
            name.setSingleLine(true);
            name.setEllipsize(android.text.TextUtils.TruncateAt.END);
            name.setTextColor(Color.parseColor("#101418"));
            name.setTypeface(null, android.graphics.Typeface.BOLD);

            TextView meta = new TextView(MainActivity.this);
            meta.setText(a.isBackup()
                    ? ("指纹 " + a.fpShort() + "  ·  " + a.sizeText() + "  ·  原 key 副本")
                    : ("指纹 " + a.fpShort() + "  ·  " + a.sizeText() + "  ·  " + a.created));
            meta.setTextSize(11);
            meta.setTextColor(Color.parseColor(a.isBackup() ? "#A3741A" : "#5B6572"));
            meta.setPadding(0, dp(3), 0, 0);

            TextView path = new TextView(MainActivity.this);
            boolean exported = a.folder != null && a.folder.length() > 0;
            path.setText(exported ? a.folder
                    : (a.isBackup() ? "只在账号库里，还没写成文件" : expectedPath(a.name) + "（未导出）"));
            path.setTextSize(10);
            path.setSingleLine(true);
            path.setEllipsize(android.text.TextUtils.TruncateAt.END);
            path.setTextColor(Color.parseColor("#9AA3B0"));
            path.setPadding(0, dp(3), 0, 0);

            col.addView(name);
            col.addView(meta);
            col.addView(path);

            boolean inUse = curFp != null && curFp.equals(a.fpShort());
            boolean dup = isDup(a);
            boolean tagSrc = accTab == 1;
            if (inUse || dup || tagSrc) {
                LinearLayout chips = new LinearLayout(MainActivity.this);
                chips.setOrientation(LinearLayout.HORIZONTAL);
                chips.setPadding(0, dp(5), 0, 0);
                int n = 0;
                if (tagSrc) {
                    chips.addView(chip(a.isBackup() ? "自动备份" : "导出",
                            a.isBackup() ? "#8A6D1F" : "#2F6BFF",
                            a.isBackup() ? "#FBF3DA" : "#EAF0FF"));
                    n++;
                }
                if (inUse) {
                    TextView c = chip("游戏在用", "#19A974", "#E8F7EF");
                    if (n == 0) chips.addView(c);
                    else {
                        LinearLayout.LayoutParams cl = new LinearLayout.LayoutParams(
                                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                        cl.setMargins(dp(6), 0, 0, 0);
                        chips.addView(c, cl);
                    }
                    n++;
                }
                if (dup) {
                    TextView c = chip("重复", "#8A6D1F", "#FBF3DA");
                    if (n == 0) chips.addView(c);
                    else {
                        LinearLayout.LayoutParams cl = new LinearLayout.LayoutParams(
                                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT);
                        cl.setMargins(dp(6), 0, 0, 0);
                        chips.addView(c, cl);
                    }
                }
                col.addView(chips);
            }

            TextView dot = new TextView(MainActivity.this);
            dot.setText(on ? "✓" : "");
            dot.setGravity(Gravity.CENTER);
            dot.setTextSize(12);
            dot.setTextColor(Color.WHITE);
            dot.setBackground(roundRect(on ? Color.parseColor("#2F6BFF") : Color.parseColor("#E6EAF1"), 20, 0, 0));
            LinearLayout.LayoutParams dl = new LinearLayout.LayoutParams(dp(22), dp(22));
            dl.setMargins(dp(10), 0, 0, 0);

            box.addView(col, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
            box.addView(dot, dl);

            LinearLayout wrap = new LinearLayout(MainActivity.this);
            wrap.setOrientation(LinearLayout.VERTICAL);
            wrap.setPadding(dp(2), dp(3), dp(2), dp(3));
            wrap.addView(box, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
            return wrap;
        }
    }

    private boolean batteryIgnored() {
        try {
            android.os.PowerManager pm = (android.os.PowerManager) getSystemService(POWER_SERVICE);
            return pm != null && pm.isIgnoringBatteryOptimizations(getPackageName());
        } catch (Throwable t) {
            return false;
        }
    }

    private boolean notifGranted() {
        try {
            android.app.NotificationManager nm = (android.app.NotificationManager) getSystemService(NOTIFICATION_SERVICE);
            return nm != null && nm.areNotificationsEnabled();
        } catch (Throwable t) {
            return false;
        }
    }

    private void askBattery() {
        try {
            Intent i = new Intent(android.provider.Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS);
            i.setData(android.net.Uri.parse("package:" + getPackageName()));
            startActivity(i);
        } catch (Throwable t) {
            try {
                startActivity(new Intent(android.provider.Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS));
            } catch (Throwable ignored) {
            }
        }
    }

    private void askNotif() {
        try {
            if (android.os.Build.VERSION.SDK_INT >= 33) {
                requestPermissions(new String[]{"android.permission.POST_NOTIFICATIONS"}, 0x7B);
            } else {
                Intent i = new Intent(android.provider.Settings.ACTION_APP_NOTIFICATION_SETTINGS);
                i.putExtra(android.provider.Settings.EXTRA_APP_PACKAGE, getPackageName());
                startActivity(i);
            }
        } catch (Throwable ignored) {
        }
    }

    private boolean storageGranted() {
        try {
            if (android.os.Build.VERSION.SDK_INT >= 30) {
                return Environment.isExternalStorageManager();
            }
            return checkSelfPermission("android.permission.WRITE_EXTERNAL_STORAGE") == PackageManager.PERMISSION_GRANTED;
        } catch (Throwable t) {
            return false;
        }
    }

    private void fillDeviceInfo() {
        try {
            android.util.DisplayMetrics dm = getResources().getDisplayMetrics();
            if (rowResVal != null) rowResVal.setText(dm.widthPixels + "×" + dm.heightPixels + "  ·  " + dm.densityDpi + "dpi");
            if (rowGameVerVal != null) {
                String gv = "未安装";
                try {
                    gv = getPackageManager().getPackageInfo(PKG, 0).versionName;
                } catch (Throwable ignored) {
                }
                rowGameVerVal.setText(gv);
            }
            String vn = "?";
            long vc = 0;
            android.content.pm.PackageInfo pi = getPackageManager().getPackageInfo(getPackageName(), 0);
            vn = pi.versionName == null ? "?" : pi.versionName;
            vc = android.os.Build.VERSION.SDK_INT >= 28 ? pi.getLongVersionCode() : pi.versionCode;
            if (rowVerVal != null) rowVerVal.setText(vn + " (" + vc + ")");
        } catch (Throwable ignored) {
        }
    }

    private TextView value(int unused, String text) {
        TextView v = new TextView(this);
        v.setText(text);
        v.setTextSize(13);
        v.setTextColor(Color.parseColor("#8A93A0"));
        return v;
    }

    /** 一行：左边标题 + 右边一个明显的「更改」按钮，路径显示在下面一行。 */
    private LinearLayout rowWithButton(TextView val, String label, String btnText, View.OnClickListener click) {
        LinearLayout r = new LinearLayout(this);
        r.setOrientation(LinearLayout.VERTICAL);
        r.setPadding(dp(2), dp(12), dp(2), dp(12));
        LinearLayout top = new LinearLayout(this);
        top.setOrientation(LinearLayout.HORIZONTAL);
        top.setGravity(Gravity.CENTER_VERTICAL);
        TextView l = new TextView(this);
        l.setText(label);
        l.setTextSize(14);
        l.setTextColor(Color.parseColor("#1B1F24"));
        top.addView(l, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        Button b = mkBtn(btnText, true);
        b.setTextSize(12);
        b.setPadding(dp(16), dp(6), dp(16), dp(6));
        top.addView(b);
        r.addView(top);
        val.setTextSize(12);
        val.setPadding(0, dp(5), 0, 0);
        r.addView(val);
        b.setOnClickListener(click);
        r.setClickable(true);
        r.setOnClickListener(click);
        return r;
    }

    private LinearLayout rowWith(TextView val, String label, View.OnClickListener click) {
        LinearLayout r = new LinearLayout(this);
        r.setOrientation(LinearLayout.HORIZONTAL);
        r.setGravity(Gravity.CENTER_VERTICAL);
        r.setPadding(dp(2), dp(13), dp(2), dp(13));
        TextView l = new TextView(this);
        l.setText(label);
        l.setTextSize(14);
        l.setTextColor(Color.parseColor("#1B1F24"));
        r.addView(l, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
        r.addView(val);
        if (click != null) {
            r.setClickable(true);
            r.setOnClickListener(click);
        }
        return r;
    }

    private View divider() {
        View v = new View(this);
        v.setBackgroundColor(Color.parseColor("#EFF1F5"));
        v.setLayoutParams(new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));
        return v;
    }

    private LinearLayout.LayoutParams cardParams(float weight) {
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                weight > 0 ? 0 : ViewGroup.LayoutParams.WRAP_CONTENT,
                weight > 0 ? weight : 0f);
        lp.setMargins(0, dp(5), 0, dp(5));
        return lp;
    }

    private LinearLayout card() {
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setBackground(roundRect(Color.WHITE, 16, Color.parseColor("#EBEEF3"), 1));
        c.setPadding(dp(14), dp(4), dp(14), dp(8));
        return c;
    }

    private android.graphics.drawable.Drawable roundRect(int color, int radiusDp, int strokeColor, int strokeDp) {
        android.graphics.drawable.GradientDrawable g = new android.graphics.drawable.GradientDrawable();
        g.setColor(color);
        g.setCornerRadius(dp(radiusDp));
        if (strokeDp > 0) g.setStroke(dp(strokeDp), strokeColor);
        return g;
    }

    private TextView caption(String s) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(11);
        t.setTextColor(Color.parseColor("#9AA3B0"));
        t.setPadding(dp(2), dp(10), 0, dp(2));
        return t;
    }

    private Button mkBtn(String text, boolean primary) {
        Button b = new Button(this);
        b.setText(text);
        b.setAllCaps(false);
        b.setTextSize(13);
        b.setTextColor(primary ? Color.WHITE : Color.parseColor("#2B3442"));
        if (primary) {
            b.setBackground(roundRect(Color.parseColor("#2F6BFF"), 10, 0, 0));
        } else {
            b.setBackground(roundRect(Color.WHITE, 10, Color.parseColor("#DCE1E8"), 1));
        }
        b.setMinHeight(dp(42));
        b.setMinWidth(0);
        b.setPadding(dp(6), 0, dp(6), 0);
        b.setStateListAnimator(null);
        b.setElevation(0);
        return b;
    }

    private LinearLayout.LayoutParams weight() {
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        p.setMargins(dp(3), dp(6), dp(3), 0);
        return p;
    }

    private LinearLayout.LayoutParams weightWide() {
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.4f);
        p.setMargins(dp(3), dp(6), dp(3), 0);
        return p;
    }

    private void log(final String s) {
        android.util.Log.i("HSK", s);
        runOnUiThread(new Runnable() {
            public void run() {
                tvLog.append(s + "\n");
                logScroll.post(new Runnable() {
                    public void run() {
                        logScroll.fullScroll(View.FOCUS_DOWN);
                    }
                });
            }
        });
    }

    private void toast(final String s) {
        runOnUiThread(new Runnable() {
            public void run() {
                Toast.makeText(MainActivity.this, s, Toast.LENGTH_SHORT).show();
            }
        });
    }

    private void updateState() {
        boolean gameInstalled = isInstalled(PKG);
        boolean alive = shizukuAlive();
        boolean granted = alive && shizukuGrantedNow();
        int okColor = Color.parseColor("#2F6BFF");
        int noColor = Color.parseColor("#E5484D");
        int grayColor = Color.parseColor("#8A93A0");
        if (rowRootVal != null) {
            rowRootVal.setText(!rootChecked ? "检测中…" : (hasRoot ? "已授权" : "未授权"));
            rowRootVal.setTextColor(!rootChecked ? grayColor : (hasRoot ? okColor : noColor));
        }
        if (rowGameVal != null) {
            rowGameVal.setText(game.label + (gameInstalled ? " · 已安装" : " · 未安装"));
            rowGameVal.setTextColor(gameInstalled ? okColor : noColor);
        }
        if (rowShzkVal != null) {
            rowShzkVal.setText(!alive ? "未连接" : (granted ? "已授权" : "待授权"));
            rowShzkVal.setTextColor(!alive ? noColor : (granted ? okColor : grayColor));
        }
        if (rowSvcVal != null) {
            String svc;
            int sc;
            if (hasRoot) { svc = "Root 已授权"; sc = okColor; }
            else if (granted) { svc = "Shizuku 已授权"; sc = okColor; }
            else { svc = "未授权"; sc = noColor; }
            rowSvcVal.setText(svc);
            rowSvcVal.setTextColor(sc);
            if (rowModeVal != null) {
                rowModeVal.setText(hasRoot ? "Root 直接读写" : (granted ? "免 root（Shizuku）" : "未授权，无法读写游戏目录"));
                rowModeVal.setTextColor(granted || hasRoot ? okColor : noColor);
            }
        }
        if (rowBatteryVal != null) {
            boolean bi = batteryIgnored();
            rowBatteryVal.setText(bi ? "已加白名单" : "点此去设置");
            rowBatteryVal.setTextColor(bi ? okColor : grayColor);
        }
        if (rowNotifVal != null) {
            boolean nf = notifGranted();
            rowNotifVal.setText(nf ? "已开启" : "点此开启");
            rowNotifVal.setTextColor(nf ? okColor : grayColor);
        }
        if (rowStoreVal != null) {
            boolean sg = storageGranted();
            rowStoreVal.setText(sg ? "已授权" : "点此授权");
            rowStoreVal.setTextColor(sg ? okColor : grayColor);
        }
        if (rowPermVal != null) {
            rowPermVal.setText(!alive ? "未连接" : (granted ? "已授权" : "点此授权"));
            rowPermVal.setTextColor(!alive ? noColor : (granted ? okColor : grayColor));
        }
        if (rowCount != null) rowCount.setText(countAccounts() + " 个账号 · " + countBackups() + " 个备份");
        if (tvState != null) {
            Account a = selected();
            tvState.setText(a == null ? "已选：无" : "已选：" + a.name + "  ·  " + a.fp());
        }
        refreshAccountsView();
        styleGameBtns();
        if (rowSelVal != null) {
            Account a = selected();
            rowSelVal.setText(a == null ? "未选择" : a.name + "  ·  " + a.fp());
            rowSelVal.setTextColor(a == null ? grayColor : okColor);
        }
    }

    private boolean isInstalled(String pkg) {
        try {
            getPackageManager().getPackageInfo(pkg, 0);
            return true;
        } catch (Exception ignored) {
        }
        try {
            if (new File("/sdcard/Android/data/" + pkg).exists()) return true;
            if (new File(EXT_DIR).exists()) return true;
            if (new File(EXT_KEY).exists()) return true;
        } catch (Exception ignored) {
        }
        return false;
    }

    private String findGamePackages() {
        StringBuilder sb = new StringBuilder();
        try {
            java.util.List<android.content.pm.PackageInfo> all = getPackageManager().getInstalledPackages(0);
            for (android.content.pm.PackageInfo pi : all) {
                String n = pi.packageName;
                if (n != null && (n.contains("housamo") || n.contains("lifewonders"))) {
                    if (sb.length() > 0) sb.append(", ");
                    sb.append(n);
                }
            }
        } catch (Exception ignored) {
        }
        return sb.toString();
    }

    private void askStorage() {
        if (Build.VERSION.SDK_INT >= 30) {
            try {
                Intent i = new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION);
                i.setData(Uri.parse("package:" + getPackageName()));
                startActivity(i);
                return;
            } catch (Exception ignored) {
            }
            try {
                startActivity(new Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION));
                return;
            } catch (Exception ignored) {
            }
        }
        requestPermissions(new String[]{"android.permission.READ_EXTERNAL_STORAGE", "android.permission.WRITE_EXTERNAL_STORAGE"}, 1);
    }

    // ---------- 进程 ----------

    static class Res {
        int code = -1;
        byte[] out = new byte[0];
        String err = "";
    }

    private Thread drain(final InputStream in, final ByteArrayOutputStream sink) {
        Thread t = new Thread(new Runnable() {
            public void run() {
                byte[] buf = new byte[8192];
                try {
                    int n;
                    while ((n = in.read(buf)) > 0) sink.write(buf, 0, n);
                } catch (Exception ignored) {
                } finally {
                    try {
                        in.close();
                    } catch (Exception ignored) {
                    }
                }
            }
        });
        t.setDaemon(true);
        t.start();
        return t;
    }

    private Res run(String[] argv, int timeoutMs) {
        Res r = new Res();
        Process p = null;
        try {
            p = new ProcessBuilder(argv).start();
            final Process fp = p;
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            ByteArrayOutputStream be = new ByteArrayOutputStream();
            Thread t1 = drain(fp.getInputStream(), bo);
            Thread t2 = drain(fp.getErrorStream(), be);
            Thread killer = new Thread(new Runnable() {
                public void run() {
                    try {
                        Thread.sleep(timeoutMs);
                        fp.destroy();
                    } catch (Exception ignored) {
                    }
                }
            });
            killer.setDaemon(true);
            killer.start();
            r.code = p.waitFor();
            t1.join(1500);
            t2.join(1500);
            r.out = bo.toByteArray();
            r.err = new String(be.toByteArray(), "UTF-8");
        } catch (Exception e) {
            r.err = e.toString();
        } finally {
            if (p != null) p.destroy();
        }
        return r;
    }

    private Res su(String cmd, int timeoutMs) {
        return run(new String[]{"su", "-c", cmd}, timeoutMs);
    }

    private boolean checkRoot() {
        Res r = su("id", 15000);
        String s = new String(r.out);
        return r.code == 0 && s.contains("uid=0");
    }

    // ---------- Shizuku（免 root 的 shell 通道）----------

    private boolean shizukuAlive() {
        try {
            return rikka.shizuku.Shizuku.pingBinder();
        } catch (Throwable t) {
            return false;
        }
    }

    private boolean shizukuGrantedNow() {
        try {
            return rikka.shizuku.Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED;
        } catch (Throwable t) {
            return false;
        }
    }

    private boolean shizukuReady() {
        return shizukuAlive() && shizukuGrantedNow();
    }

    private boolean hasShell() {
        return hasRoot || shizukuReady();
    }

    /** 用 Shizuku 以 shell 身份执行命令（相当于 adb shell，不需要 root）。 */
    private Res sh(String cmd, int timeoutMs) {
        Res r = new Res();
        Process p = null;
        try {
            p = rikka.shizuku.Shizuku.newProcess(new String[]{"sh", "-c", cmd}, null, null);
            final Process fp = p;
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            ByteArrayOutputStream be = new ByteArrayOutputStream();
            Thread t1 = drain(fp.getInputStream(), bo);
            Thread t2 = drain(fp.getErrorStream(), be);
            Thread killer = new Thread(new Runnable() {
                public void run() {
                    try {
                        Thread.sleep(timeoutMs);
                        fp.destroy();
                    } catch (Exception ignored) {
                    }
                }
            });
            killer.setDaemon(true);
            killer.start();
            r.code = p.waitFor();
            t1.join(1500);
            t2.join(1500);
            r.out = bo.toByteArray();
            r.err = new String(be.toByteArray(), "UTF-8");
        } catch (Throwable e) {
            r.err = "shizuku: " + e;
        } finally {
            if (p != null) p.destroy();
        }
        return r;
    }

    /** 通过 Shizuku 以 shell 身份执行，并把 data 灌进 stdin（用于原地覆盖写文件，保留原属主/权限）。 */
    private Res shWithInput(String cmd, byte[] data, int timeoutMs) {
        Res r = new Res();
        Process p = null;
        try {
            p = rikka.shizuku.Shizuku.newProcess(new String[]{"sh", "-c", cmd}, null, null);
            final Process fp = p;
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            ByteArrayOutputStream be = new ByteArrayOutputStream();
            Thread t1 = drain(fp.getInputStream(), bo);
            Thread t2 = drain(fp.getErrorStream(), be);
            OutputStream os = fp.getOutputStream();
            os.write(data);
            os.flush();
            os.close();
            Thread killer = new Thread(new Runnable() {
                public void run() {
                    try {
                        Thread.sleep(timeoutMs);
                        fp.destroy();
                    } catch (Exception ignored) {
                    }
                }
            });
            killer.setDaemon(true);
            killer.start();
            r.code = p.waitFor();
            t1.join(1500);
            t2.join(1500);
            r.out = bo.toByteArray();
            r.err = new String(be.toByteArray(), "UTF-8");
        } catch (Throwable e) {
            r.err = "shizuku: " + e;
        } finally {
            if (p != null) p.destroy();
        }
        return r;
    }

    /** 统一入口：优先 root，其次 Shizuku。 */
    private Res shell(String cmd, int timeoutMs) {
        if (hasRoot) return su(cmd, timeoutMs);
        if (shizukuReady()) return sh(cmd, timeoutMs);
        Res r = new Res();
        r.err = "没有可用权限（既无 root，也未连接 Shizuku）";
        return r;
    }

    private void askShizuku() {
        final String PKG_SHI = "moe.shizuku.privileged.api";
        if (!shizukuAlive()) {
            boolean installed = isInstalled(PKG_SHI);
            if (!installed) {
                log("[Shizuku] 未安装 Shizuku，已引导下载。");
                new AlertDialog.Builder(this)
                        .setTitle("未安装 Shizuku")
                        .setMessage("Shizuku 能把 adb 权限借给本应用，让 Android 11+ 不用 root 也能读写游戏目录。\n\n装好后打开它，按提示用「无线调试」启动，再回到这里点 Shizuku 授权。")
                        .setPositiveButton("去下载", new android.content.DialogInterface.OnClickListener() {
                            public void onClick(android.content.DialogInterface d, int w) {
                                openUrl("https://github.com/RikkaApps/Shizuku/releases/latest");
                            }
                        })
                        .setNegativeButton("取消", null)
                        .show();
                return;
            }
            log("[Shizuku] 已安装但服务未运行，请先启动 Shizuku。");
            new AlertDialog.Builder(this)
                    .setTitle("Shizuku 未启动")
                    .setMessage("打开 Shizuku 后按它的提示启动服务（重启手机后需要重新启动），再回来点「刷新」。")
                    .setPositiveButton("打开 Shizuku", new android.content.DialogInterface.OnClickListener() {
                        public void onClick(android.content.DialogInterface d, int w) {
                            Intent i = getPackageManager().getLaunchIntentForPackage(PKG_SHI);
                            if (i != null) startActivity(i);
                            else openUrl("https://github.com/RikkaApps/Shizuku/releases/latest");
                        }
                    })
                    .setNegativeButton("取消", null)
                    .show();
            return;
        }
        if (shizukuGrantedNow()) {
            log("[Shizuku] 已授权，可以直接免 root 提取/导入。");
            toast("Shizuku 已授权");
            updateState();
            return;
        }
        try {
            rikka.shizuku.Shizuku.requestPermission(REQ_SHIZUKU);
            log("[Shizuku] 已弹出授权请求，请在 Shizuku 中点击「允许」。");
        } catch (Throwable t) {
            log("[Shizuku] 请求授权失败：" + t);
        }
    }

    private void openUrl(String url) {
        try {
            startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));
        } catch (Exception e) {
            toast("无法打开浏览器：" + url);
        }
    }

    // ---------- 文件读写 ----------

    private static boolean looksLikeKey(byte[] d) {
        if (d == null || d.length < 8 || d.length > 8192) return false;
        int printable = 0;
        for (byte b : d) {
            int c = b & 0xFF;
            if (c == 9 || c == 10 || c == 13) {
                printable++;
            } else if (c >= 32 && c < 127) {
                printable++;
            } else {
                return false;
            }
        }
        return printable == d.length;
    }

    private byte[] directRead(String path) {
        File f = new File(path);
        if (!f.exists() || !f.canRead()) return null;
        FileInputStream in = null;
        try {
            in = new FileInputStream(f);
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
            return bo.toByteArray();
        } catch (Exception e) {
            return null;
        } finally {
            try {
                if (in != null) in.close();
            } catch (Exception ignored) {
            }
        }
    }

    private byte[] readKeyAt(String path) {
        boolean prefs = path.endsWith(".xml");
        byte[] d = directRead(path);
        if (d != null && (prefs ? d.length > 0 : looksLikeKey(d))) return trim(d);
        Res r = shell("cat '" + path + "' 2>/dev/null", 15000);
        if (r.code == 0 && r.out.length > 0 && (prefs ? true : looksLikeKey(r.out))) return trim(r.out);
        return null;
    }

    private static byte[] trim(byte[] d) {
        int s = 0, e = d.length;
        while (s < e && (d[s] == ' ' || d[s] == '\n' || d[s] == '\r' || d[s] == '\t')) s++;
        while (e > s && (d[e - 1] == ' ' || d[e - 1] == '\n' || d[e - 1] == '\r' || d[e - 1] == '\t')) e--;
        byte[] o = new byte[e - s];
        System.arraycopy(d, s, o, 0, e - s);
        return o;
    }

    private String extractFromPrefs(String xml) {
        int i = xml.indexOf("name=\"AuthKey\"");
        if (i < 0) i = xml.indexOf("name='AuthKey'");
        if (i < 0) return null;
        int gt = xml.indexOf('>', i);
        if (gt < 0) return null;
        int lt = xml.indexOf('<', gt + 1);
        if (lt < 0) return null;
        String v = xml.substring(gt + 1, lt).trim();
        return v.length() >= 8 ? v : null;
    }

    // ---------- 账号库 ----------

    private void loadVault() {
        accounts.clear();
        SharedPreferences sp = getSharedPreferences(VAULT, Context.MODE_PRIVATE);
        String raw = sp.getString(VAULT_KEY, "[]");
        try {
            JSONArray arr = new JSONArray(raw);
            for (int i = 0; i < arr.length(); i++) {
                Account a = Account.fromJson(arr.getJSONObject(i));
                // 老版本把「从导出文件夹扫到的 key」也存进了库，这里迁移成正常账号（不再当导出条目）
                if (a.note != null && a.note.contains("来自导出文件夹")) a.note = "";
                if (a.key != null && a.key.length() > 0) accounts.add(a);
            }
        } catch (Exception e) {
            log("[库] 读取失败：" + e);
        }
    }

    private void saveVault() {
        try {
            JSONArray arr = new JSONArray();
            for (Account a : accounts) arr.put(a.toJson());
            getSharedPreferences(VAULT, Context.MODE_PRIVATE).edit().putString(VAULT_KEY, arr.toString()).apply();
        } catch (Exception e) {
            log("[库] 保存失败：" + e);
        }
    }

    private void refreshList() {
        adapter.notifyDataSetChanged();
        updateState();
    }

    private Account selected() {
        if (list == null) return null;
        int p = list.getCheckedItemPosition();
        if (p < 0 || p >= accView.size()) return null;
        return accView.get(p);
    }

    private void switchAccTab(int tab) {
        accTab = tab;
        if (list != null) list.clearChoices();
        refreshAccountsView();
        updateState();
    }

    private void selectAccount(Account a) {
        if (list == null || a == null) return;
        int i = accView.indexOf(a);
        if (i >= 0) list.setItemChecked(i, true);
    }

    /** 这条记录是不是属于当前游戏。 */
    private boolean inGame(Account a) {
        if (a == null) return false;
        String g = (a.game == null || a.game.length() == 0) ? "housamo" : a.game;
        return g.equals(game.id);
    }

    private int countAccounts() {
        int n = 0;
        for (Account a : accounts) if (!a.isBackup() && inGame(a)) n++;
        return n;
    }

    /** 只在「导出文件夹里扫到、但账号库里还没有」的临时条目（不入库）。 */
    private boolean isExportEntry(Account a) {
        return a != null && exportEntries.contains(a);
    }

    private int countExportEntries() {
        return exportEntries.size();
    }

    private int countBackups() {
        int n = 0;
        for (Account a : accounts) if (a.isBackup() && inGame(a)) n++;
        return n;
    }

    private void styleSeg(Button b, boolean active) {
        if (b == null) return;
        if (active) {
            b.setTextColor(Color.WHITE);
            b.setBackground(roundRect(Color.parseColor("#2F6BFF"), 10, 0, 0));
        } else {
            b.setTextColor(Color.parseColor("#5B6572"));
            b.setBackground(roundRect(Color.parseColor("#F3F5F9"), 10, 0, 0));
        }
    }

    private void refreshAccountsView() {
        if (accView == null) return;
        accView.clear();
        // 新的排前面：账号库是按时间追加的，倒序显示更符合直觉
        for (int i = accounts.size() - 1; i >= 0; i--) {
            Account a = accounts.get(i);
            if (!inGame(a)) continue;
            if (a.isBackup() == (accTab == 1)) accView.add(a);
        }
        if (accTab == 1) {
            // 导出文件夹里扫到、库里还没有的 key 也列在备份分段里（只用于查看/导入，不入库）
            for (int i = exportEntries.size() - 1; i >= 0; i--) accView.add(exportEntries.get(i));
        }
        int na = countAccounts(), nb = countBackups() + countExportEntries();
        if (segA != null) segA.setText("账号 " + na);
        if (segB != null) segB.setText("备份 " + nb);
        styleSeg(segA, accTab == 0);
        styleSeg(segB, accTab == 1);
        if (bMain != null) bMain.setText("导入到游戏");
        if (bRename != null) bRename.setVisibility(accTab == 0 ? View.VISIBLE : View.GONE);
        if (tvAccHint != null) {
            String cur = curFp == null
                    ? (curFpLoaded ? "读不到（需要 Shizuku 或 Root 权限）" : "读取中…")
                    : curFp;
            tvAccHint.setText("游戏里现在用的：指纹 " + cur + "\n"
                    + (accTab == 0
                    ? "选一个账号 →「导入到游戏」覆盖当前登录（导入前自动备份现在的 key）。改名 / 删除在第二排，长按有更多操作。"
                    : "自动备份（每次导入前存下的原 key）和导出文件夹里的 key 都在这里。选中一条点「导入到游戏」就能还原回去。"));
        }
        if (emptyHint != null) {
            if (accView.isEmpty()) {
                emptyHint.setVisibility(View.VISIBLE);
                emptyHint.setText(accTab == 0
                        ? "还没有账号。去「任务」页点「提取当前账号的 key」。"
                        : "还没有备份或导出的 key。每次导入前，游戏里原来的 key 会自动存到这里；「导出位置」文件夹里的 key 也会列进来。");
            } else {
                emptyHint.setVisibility(View.GONE);
            }
        }
        if (adapter != null) adapter.notifyDataSetChanged();
    }

    // ---------- 业务 ----------

    private void doExtract() {
        log("--- 开始提取 ---");
        pool.execute(new Runnable() {
            public void run() {
                String[] cands = new String[]{EXT_KEY, PREFS1, PREFS2};
                String found = null;
                String key = null;
                for (String p : cands) {
                    byte[] d = readKeyAt(p);
                    if (d != null) {
                        key = new String(d).trim();
                        if (p.endsWith(".xml")) {
                            String v = extractFromPrefs(new String(d));
                            if (v != null) key = v;
                        }
                        if (key != null && key.length() >= 8) {
                            found = p;
                            break;
                        }
                    }
                }
                if (key == null) {
                    byte[] scan = scanByFind();
                    if (scan != null) {
                        key = new String(scan).trim();
                        found = "(find 扫描)";
                    }
                }
                if (key == null || key.length() < 8) {
                    log("[失败] 未找到 AuthKey。请确认游戏已登录至少一次；Android 11+ 需要 root 或 Shizuku。");
                    toast("未找到 AuthKey");
                    return;
                }
                final String theKey = key;
                final String source = found == null ? "?" : found;
                runOnUiThread(new Runnable() {
                    public void run() {
                        askNameThenSave(theKey, source);
                    }
                });
            }
        });
    }

    /** 提取成功后：先让用户起名，再入库并导出到文件夹。 */
    private void askNameThenSave(final String key, final String source) {
        final String defName = "设备 " + Build.MODEL + " " + stamp();
        final EditText et = new EditText(this);
        et.setSingleLine(true);
        et.setInputType(InputType.TYPE_CLASS_TEXT);
        et.setText(defName);
        et.setSelection(defName.length());
        new AlertDialog.Builder(this)
                .setTitle("给这个账号取个名字")
                .setMessage("会同时导出到 手机存储/Download/东放Key/<名字>/AuthKey.txt")
                .setView(et)
                .setPositiveButton("保存", new android.content.DialogInterface.OnClickListener() {
                    public void onClick(android.content.DialogInterface d, int w) {
                        String n = et.getText().toString().trim();
                        addAccount(n.length() > 0 ? n : defName, key, source);
                    }
                })
                .setNegativeButton("用默认名", new android.content.DialogInterface.OnClickListener() {
                    public void onClick(android.content.DialogInterface d, int w) {
                        addAccount(defName, key, source);
                    }
                })
                .show();
    }

    /** 用 MediaStore 查 Download/东放Key/<名字>/AuthKey.txt 是否已存在。 */
    private boolean exportedExists(String name) {
        if (android.os.Build.VERSION.SDK_INT >= 29) {
            android.database.Cursor c = null;
            try {
                android.net.Uri uri = android.provider.MediaStore.Downloads.EXTERNAL_CONTENT_URI;
                String[] proj = new String[]{android.provider.MediaStore.Downloads._ID};
                String sel = android.provider.MediaStore.Downloads.RELATIVE_PATH + " LIKE ? AND "
                        + android.provider.MediaStore.Downloads.DISPLAY_NAME + " = ?";
                String[] args = new String[]{"Download/东放Key/" + safeName(name) + "/%", "AuthKey.txt"};
                c = getContentResolver().query(uri, proj, sel, args, null);
                if (c != null && c.getCount() > 0) return true;
            } catch (Throwable ignored) {
            } finally {
                if (c != null) try { c.close(); } catch (Throwable ignored) {}
            }
        }
        try {
            File f = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),
                    "东放Key/" + safeName(name) + "/AuthKey.txt");
            return f.exists();
        } catch (Throwable ignored) {
            return false;
        }
    }

    /** 老版本存的账号没有 folder 记录，启动时补导一次，列表里才能显示真实路径。 */
    private void autoExportMissing() {
        try {
            autoExportMissingInner();
        } catch (Throwable t) {
            log("[导出] 自动补导出失败：" + t);
        }
    }

    private void autoExportMissingInner() {
        boolean changed = false;
        for (int i = 0; i < accounts.size(); i++) {
            Account a = accounts.get(i);
            if (!inGame(a)) continue;
            if (a.folder == null || a.folder.length() == 0) {
                if (exportedExists(a.name)) {
                    a.folder = "/storage/emulated/0/" + exportRelPrefix() + safeName(a.name) + "/AuthKey.txt";
                    changed = true;
                    continue;
                }
                String out = exportKeyFolder(a.name, a.key);
                if (out != null) {
                    a.folder = out;
                    changed = true;
                }
            }
        }
        if (!changed) return;
        saveVault();
        runOnUiThread(new Runnable() {
            public void run() {
                refreshList();
                log("[导出] 已把缺路径的 key 补导出到 Download/东放Key/");
            }
        });
    }

    private void addAccount(String name, String key, String source) {
        Account a = new Account(name, key);
        a.game = game.id;
        a.note = "来源：" + source;
        accounts.add(a);
        saveVault();
        if (accTab != 0) { accTab = 0; }
        refreshList();
        selectAccount(a);
        updateState();
        log("[成功] 已加入账号库：" + a.name + " (" + a.fp() + ")");
        String out = exportKeyFolder(name, key);
        if (out != null) {
            a.folder = out;
            saveVault();
            refreshList();
            log("[导出] " + out);
            toast("已保存并导出");
        } else {
            log("[导出] 写 Download 失败：可点「存储权限」授权后再导一次。");
            toast("已保存（导出失败）");
        }
    }

    /** 账号名 -> 合法文件夹名（过滤非法字符、限长）。 */
    static String safeName(String name) {
        StringBuilder nb = new StringBuilder();
        for (int i = 0; i < name.length(); i++) {
            char c = name.charAt(i);
            if (Character.isLetterOrDigit(c) || c == ' ' || c == '-' || c == '_' || c == '.') nb.append(c);
            else nb.append('_');
        }
        String safe = nb.toString().trim();
        if (safe.length() == 0) safe = "账号";
        if (safe.length() > 40) safe = safe.substring(0, 40);
        return safe;
    }

    /** 预期导出路径，用于列表展示。 */
    static String expectedPath(String name) {
        return "Download/东放Key/" + safeName(name) + "/AuthKey.txt";
    }

    /** 把 key 原样写进 Download/东放Key/<名字>/AuthKey.txt，返回可读路径或 null。 */
    private void checkUpdate(final boolean manual) {
        if (manual && rowUpdateVal != null) rowUpdateVal.setText("检查中…");
        new Thread(new Runnable() {
            public void run() {
                String tag = null;
                String url = null;
                String apk = null;
                try {
                    java.net.HttpURLConnection c = (java.net.HttpURLConnection) new java.net.URL(
                            "https://api.github.com/repos/fenghuo6183/HousamoAuthKeyManager/releases/latest").openConnection();
                    c.setConnectTimeout(8000);
                    c.setReadTimeout(8000);
                    c.setRequestProperty("Accept", "application/vnd.github+json");
                    c.setRequestProperty("User-Agent", "HousamoAuthKeyManager");
                    java.io.InputStream in = c.getInputStream();
                    java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
                    byte[] buf = new byte[4096];
                    int n;
                    while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
                    in.close();
                    String body = new String(bo.toByteArray(), "UTF-8");
                    java.util.regex.Matcher m1 = java.util.regex.Pattern.compile("\"tag_name\"\\s*:\\s*\"([^\"]+)\"").matcher(body);
                    if (m1.find()) tag = m1.group(1);
                    java.util.regex.Matcher m2 = java.util.regex.Pattern.compile("\"html_url\"\\s*:\\s*\"([^\"]+)\"").matcher(body);
                    if (m2.find()) url = m2.group(1);
                    java.util.regex.Matcher m3 = java.util.regex.Pattern.compile("\"browser_download_url\"\\s*:\\s*\"([^\"]+\\.apk)\"").matcher(body);
                    if (m3.find()) apk = m3.group(1);
                } catch (Throwable t) {
                    if (manual) {
                        runOnUiThread(new Runnable() {
                            public void run() {
                                if (rowUpdateVal != null) rowUpdateVal.setText("检查失败（网络）");
                            }
                        });
                        log("[更新] 检查失败：" + t);
                    }
                    return;
                }
                final String ver = tag == null ? "" : tag.replace("v", "");
                final String apkUrl = apk;
                final String rel = url == null ? "https://github.com/fenghuo6183/HousamoAuthKeyManager/releases" : url;
                final int cmp = ver.length() == 0 ? 0 : compareVer(ver, CURRENT_VER);
                runOnUiThread(new Runnable() {
                    public void run() {
                        if (rowUpdateVal != null) {
                            rowUpdateVal.setText(cmp > 0 ? "发现 " + ver + "，点此更新" : "已是最新版 " + CURRENT_VER);
                            rowUpdateVal.setTextColor(cmp > 0 ? Color.parseColor("#2F6BFF") : Color.parseColor("#9AA3B0"));
                        }
                        if (cmp > 0) {
                            log("[更新] 发现新版本 " + ver + (apkUrl == null ? "（该版本没有 APK 资产，将跳网页）" : ""));
                            if (apkUrl != null) {
                                if (manual) promptedUpdate = "";
                                if (!promptedUpdate.equals(ver)) showUpdatePrompt(ver, apkUrl);
                            } else {
                                toast("发现新版本 " + ver);
                            }
                            if (rowUpdateVal != null) {
                                rowUpdateVal.setOnClickListener(new View.OnClickListener() {
                                    public void onClick(View v) {
                                        if (apkUrl != null) { promptedUpdate = ""; showUpdatePrompt(ver, apkUrl); }
                                        else openUrl(rel);
                                    }
                                });
                            }
                        } else {
                            if (rowUpdateVal != null) rowUpdateVal.setOnClickListener(new View.OnClickListener() {
                                public void onClick(View v) { openUrl(rel); }
                            });
                        }
                    }
                });
            }
        }).start();
    }

    // ---------- 应用内更新 ----------
    private void showUpdatePrompt(final String ver, final String apkUrl) {
        promptedUpdate = ver;
        try {
            new AlertDialog.Builder(this)
                    .setTitle("发现新版本 " + ver)
                    .setMessage("当前版本 " + CURRENT_VER + "。\n\n可以直接在这里下载并覆盖安装，账号库和导出文件夹里的 key 都不会动。\n\n更新包来自本项目的 GitHub Release。")
                    .setPositiveButton("立即更新", new android.content.DialogInterface.OnClickListener() {
                        public void onClick(android.content.DialogInterface d, int w) { downloadUpdate(ver, apkUrl); }
                    })
                    .setNegativeButton("稍后", null)
                    .setNeutralButton("去网页", new android.content.DialogInterface.OnClickListener() {
                        public void onClick(android.content.DialogInterface d, int w) { openUrl(apkUrl); }
                    })
                    .show();
        } catch (Throwable t) {
            log("[更新] 弹窗失败：" + t);
        }
    }

    private void downloadUpdate(final String ver, final String apkUrl) {
        final android.app.ProgressDialog pd = new android.app.ProgressDialog(this);
        pd.setTitle("正在下载 " + ver);
        pd.setMessage("0%");
        pd.setProgressStyle(android.app.ProgressDialog.STYLE_HORIZONTAL);
        pd.setMax(100);
        pd.setCancelable(false);
        try { pd.show(); } catch (Throwable ignored) { }
        new Thread(new Runnable() {
            public void run() {
                File out = null;
                String err = null;
                try {
                    java.net.HttpURLConnection c = (java.net.HttpURLConnection) new java.net.URL(apkUrl).openConnection();
                    c.setConnectTimeout(15000);
                    c.setReadTimeout(60000);
                    c.setInstanceFollowRedirects(true);
                    c.setRequestProperty("User-Agent", "HousamoAuthKeyManager");
                    int total = c.getContentLength();
                    File dir = new File(getExternalFilesDir(null), "update");
                    if (!dir.exists()) dir.mkdirs();
                    out = new File(dir, "HousamoAuthKeyManager-" + ver + ".apk");
                    InputStream in = c.getInputStream();
                    FileOutputStream fo = new FileOutputStream(out);
                    byte[] buf = new byte[8192];
                    int n, got = 0, last = -1;
                    while ((n = in.read(buf)) > 0) {
                        fo.write(buf, 0, n);
                        got += n;
                        if (total > 0) {
                            final int pct = (int) (got * 100L / total);
                            if (pct != last && pct % 5 == 0) {
                                last = pct;
                                runOnUiThread(new Runnable() {
                                    public void run() { pd.setProgress(pct); pd.setMessage(pct + "%"); }
                                });
                            }
                        }
                    }
                    fo.flush();
                    fo.close();
                    in.close();
                    if (out.length() < 20000) err = "下载的文件太小，可能不是安装包";
                } catch (Throwable t) {
                    err = String.valueOf(t);
                }
                final File f = out;
                final String e = err;
                runOnUiThread(new Runnable() {
                    public void run() {
                        try { pd.dismiss(); } catch (Throwable ignored) { }
                        if (e != null || f == null) {
                            log("[更新] 下载失败：" + e);
                            toast("下载失败，可点「去网页」手动更新");
                            return;
                        }
                        log("[更新] 已下载 " + f.getAbsolutePath() + "（" + f.length() + " 字节）");
                        installApk(f);
                    }
                });
            }
        }).start();
    }

    private void installApk(File f) {
        try {
            if (Build.VERSION.SDK_INT >= 26 && !getPackageManager().canRequestPackageInstalls()) {
                pendingApk = f;
                toast("请允许「东放 Key 管家」安装应用，返回后会自动继续");
                log("[更新] 需要先允许「安装未知应用」，已打开系统设置");
                Intent i = new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:" + getPackageName()));
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(i);
                return;
            }
            pendingApk = null;
            Uri u = ApkProvider.uriFor(f);
            Intent i = new Intent(Intent.ACTION_VIEW);
            i.setDataAndType(u, "application/vnd.android.package-archive");
            i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(i);
            log("[更新] 已交给系统安装器，按提示「更新」即可，账号数据不受影响");
        } catch (Throwable t) {
            log("[更新] 启动安装失败：" + t);
            toast("启动安装失败，可点「去网页」手动更新");
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        // 每次回到 App 核对一次：游戏里的 key 变了吗
        if (list != null) curFpLoaded = false;
        refreshCurrentFp();
        if (pendingApk != null && (Build.VERSION.SDK_INT < 26 || getPackageManager().canRequestPackageInstalls())) {
            File f = pendingApk;
            pendingApk = null;
            installApk(f);
        }
    }

    private static int compareVer(String a, String b) {
        String[] x = a.split("\\.");
        String[] y = b.split("\\.");
        for (int i = 0; i < Math.max(x.length, y.length); i++) {
            int xi = i < x.length ? parseIntSafe(x[i]) : 0;
            int yi = i < y.length ? parseIntSafe(y[i]) : 0;
            if (xi != yi) return xi > yi ? 1 : -1;
        }
        return 0;
    }

    private static int parseIntSafe(String s) {
        try {
            return Integer.parseInt(s.replaceAll("[^0-9]", ""));
        } catch (Throwable t) {
            return 0;
        }
    }

    private String exportRootLabel() {
        String l = getPreferences(MODE_PRIVATE).getString("exportRootLabel", "");
        return l.length() == 0 ? "Download/东放Key/" : l;
    }

    private android.net.Uri exportRootUri() {
        String u = getPreferences(MODE_PRIVATE).getString("exportRoot", "");
        return u.length() == 0 ? null : android.net.Uri.parse(u);
    }

    private void chooseExportDir() {
        try {
            Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
            i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                    | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
            startActivityForResult(i, REQ_TREE);
        } catch (Throwable t) {
            toast("无法打开文件夹选择器");
        }
    }

    @Override
    protected void onActivityResult(int req, int res, Intent data) {
        super.onActivityResult(req, res, data);
        if (res != RESULT_OK || data == null || data.getData() == null) return;
        android.net.Uri uri = data.getData();
        if (req != REQ_TREE && req != REQ_TREE_COPY && req != REQ_TREE_BAK) return;
        try {
            getContentResolver().takePersistableUriPermission(uri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        } catch (Throwable ignored) {
        }
        if (req == REQ_TREE_COPY) {
            Account a = copyTarget;
            boolean mv = copyMove;
            copyTarget = null;
            copyMove = false;
            if (a == null) {
                toast("没有选中的 key");
                return;
            }
            doCopyToTree(uri, a, mv);
            return;
        }
        String label = treeLabel(uri);
        if (req == REQ_TREE_BAK) {
            getPreferences(MODE_PRIVATE).edit().putString("backupRoot", uri.toString())
                    .putString("backupRootLabel", label + "/").apply();
            if (rowBackupVal != null) rowBackupVal.setText(label + "/");
            log("[备份] 位置已改为：" + label + "/");
            toast("备份位置已更新");
            return;
        }
        getPreferences(MODE_PRIVATE).edit().putString("exportRoot", uri.toString()).putString("exportRootLabel", label).apply();
        if (rowExportVal != null) rowExportVal.setText(label);
        if (rowSaved != null) rowSaved.setText(label + "/");
        log("[导出] 位置已改为：" + label);
        toast("导出位置已更新");
    }

    private String exportToTree(android.net.Uri tree, String safe, byte[] data) {
        try {
            String treeId = android.provider.DocumentsContract.getTreeDocumentId(tree);
            android.net.Uri rootDoc = android.provider.DocumentsContract.buildDocumentUriUsingTree(tree, treeId);
            android.net.Uri sub = findChild(rootDoc, safe);
            if (sub == null) {
                sub = android.provider.DocumentsContract.createDocument(getContentResolver(), rootDoc, "vnd.android.document/directory", safe);
            }
            if (sub == null) return null;
            android.net.Uri old = findChild(sub, "AuthKey.txt");
            if (old != null) {
                try {
                    getContentResolver().delete(old, null, null);
                } catch (Throwable ignored) {
                }
            }
            android.net.Uri f = android.provider.DocumentsContract.createDocument(getContentResolver(), sub, "text/plain", "AuthKey.txt");
            if (f == null) return null;
            OutputStream os = getContentResolver().openOutputStream(f);
            os.write(data);
            os.flush();
            os.close();
            return f.toString();
        } catch (Throwable t) {
            log("[导出] 自定义目录写入失败：" + t);
            return null;
        }
    }

    private android.net.Uri findChild(android.net.Uri parent, String name) {
        android.database.Cursor c = null;
        try {
            android.net.Uri children = android.provider.DocumentsContract.buildChildDocumentsUriUsingTree(
                    parent, android.provider.DocumentsContract.getDocumentId(parent));
            c = getContentResolver().query(children, new String[]{
                    android.provider.DocumentsContract.Document.COLUMN_DOCUMENT_ID,
                    android.provider.DocumentsContract.Document.COLUMN_DISPLAY_NAME}, null, null, null);
            while (c != null && c.moveToNext()) {
                if (name.equals(c.getString(1))) {
                    return android.provider.DocumentsContract.buildDocumentUriUsingTree(parent, c.getString(0));
                }
            }
        } catch (Throwable ignored) {
        } finally {
            if (c != null) c.close();
        }
        return null;
    }

    private String exportKeyFolder(String name, String key) {
        String safe = safeName(name);
        byte[] data = key.getBytes();
        android.net.Uri tree = exportTreeForGame();
        if (tree != null) {
            String t = exportToTree(tree, safe, data);
            if (t != null) return exportRootLabelFull() + safe + "/AuthKey.txt";
        }
        String rel = exportRelPrefix() + safe;
        // 1) 直接写（Android 10 及以下，或已授予「所有文件访问」）
        try {
            File dir = new File(exportRootGameDir(), safe);
            if (dir.exists() || dir.mkdirs()) {
                File f = new File(dir, "AuthKey.txt");
                FileOutputStream fo = new FileOutputStream(f);
                try {
                    fo.write(data);
                    fo.flush();
                } finally {
                    fo.close();
                }
                if (f.length() == data.length) return rel + "/AuthKey.txt";
            }
        } catch (Exception e) {
            log("[导出] 直接写入失败：" + e.getMessage());
        }
        // 2) MediaStore（Android 10+，无需权限）
        if (Build.VERSION.SDK_INT >= 29) {
            OutputStream os = null;
            try {
                ContentValues cv = new ContentValues();
                cv.put(MediaStore.MediaColumns.DISPLAY_NAME, "AuthKey.txt");
                cv.put(MediaStore.MediaColumns.MIME_TYPE, "text/plain");
                cv.put(MediaStore.MediaColumns.RELATIVE_PATH, rel);
                Uri uri = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, cv);
                if (uri != null) {
                    os = getContentResolver().openOutputStream(uri);
                    if (os != null) {
                        os.write(data);
                        os.flush();
                        return rel + "/AuthKey.txt";
                    }
                }
            } catch (Exception e) {
                log("[导出] MediaStore 写入失败：" + e.getMessage());
            } finally {
                try {
                    if (os != null) os.close();
                } catch (Exception ignored) {
                }
            }
        }
        // 3) shell 兜底（root / Shizuku）
        if (hasShell()) {
            String sdir = exportRootShellDir() + "/" + safe;
            Res r = shWithInput("mkdir -p '" + sdir + "' && cat > '" + sdir + "/AuthKey.txt'", data, 20000);
            if (r.code == 0) return rel + "/AuthKey.txt";
        }
        return null;
    }

    private byte[] scanByFind() {
        if (!hasShell()) return null;
        Res r = shell("find /sdcard /data/data/" + PKG + " -name AuthKey -type f 2>/dev/null | head -5", 25000);
        String s = new String(r.out).trim();
        if (s.length() == 0) return null;
        String first = s.split("\n")[0].trim();
        log("[扫描] 找到文件：" + first);
        return readKeyAt(first);
    }

    private void doExport() {
        final Account a = selected();
        if (a == null) {
            toast("请先选中一个账号");
            return;
        }
        log("[导出] 正在导出：" + a.name);
        pool.execute(new Runnable() {
            public void run() {
                final String out = exportKeyFolder(a.name, a.key);
                runOnUiThread(new Runnable() {
                    public void run() {
                        if (out != null) {
                            a.folder = out;
                            saveVault();
                            refreshList();
                            log("[导出] " + out);
                            toast("已导出");
                        } else {
                            log("[导出] 失败：可点「存储权限」授权后再试。");
                            toast("导出失败");
                        }
                    }
                });
            }
        });
    }

    private TextView chip(String text, String fg, String bg) {
        TextView t = new TextView(this);
        t.setText(text);
        t.setTextSize(10);
        t.setTextColor(Color.parseColor(fg));
        t.setBackground(roundRect(Color.parseColor(bg), 20, 0, 0));
        t.setPadding(dp(7), dp(2), dp(7), dp(2));
        return t;
    }

    /** 账号库里有没有别的条目和它 key 一样（重复导入、多个备份都会命中）。 */
    private boolean isDup(Account a) {
        if (a.key == null || a.key.length() <= 20) return false;
        for (Account b : accounts) {
            if (b != a && inGame(b) && a.key.equals(b.key)) return true;
        }
        return false;
    }

    /** 长按账号卡片弹出的操作菜单。 */
    private void showAccMenu() {
        final Account a = selected();
        if (a == null) return;
        final java.util.ArrayList<String> items = new java.util.ArrayList<String>();
        items.add("导入到游戏");
        if (!a.isBackup()) items.add("重命名");
        items.add("删除");
        new AlertDialog.Builder(this)
                .setTitle(a.isBackup() ? a.name.replace("导入前备份", "备份") : a.name)
                .setItems(items.toArray(new String[0]), new android.content.DialogInterface.OnClickListener() {
                    public void onClick(android.content.DialogInterface d, int w) {
                        String s = items.get(w);
                        if (s.startsWith("导入")) doImport();
                        else if (s.startsWith("重命名")) doRename();
                        else doDelete();
                    }
                })
                .show();
    }

    /** 后台读一次游戏里正在用的 key，算出指纹，用来标记「游戏在用」。 */
    private void refreshCurrentFp() {
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
        if (latest != null) msg += "\n库里最新的是「" + latest.name + "」（" + latest.fpShort() + "）。";
        msg += "\n想留一份，就点「存到账号库」。";
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
    }

    private void launchGame() {
        try {
            Intent i = getPackageManager().getLaunchIntentForPackage(PKG);
            if (i == null) {
                toast("没找到游戏，请确认已安装");
                return;
            }
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            startActivity(i);
        } catch (Throwable e) {
            toast("打开游戏失败：" + e);
        }
    }

    // ---------- 复制 / 移动到其他文件夹 ----------

    private void startCopyMove() {
        final Account a = selected();
        if (a == null) {
            toast("先到「账号」页选一个 key");
            showPage(2);
            return;
        }
        new AlertDialog.Builder(this)
                .setTitle("把「" + a.name + "」放到其他文件夹")
                .setItems(new String[]{"复制一份（原来的保留）", "移动过去（删掉原来导出的那份）"},
                        new android.content.DialogInterface.OnClickListener() {
                            public void onClick(android.content.DialogInterface d, int w) {
                                copyTarget = a;
                                copyMove = (w == 1);
                                try {
                                    Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
                                    i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                                            | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
                                    startActivityForResult(i, REQ_TREE_COPY);
                                } catch (Throwable t) {
                                    toast("无法打开文件夹选择器");
                                }
                            }
                        })
                .show();
    }

    private void doCopyToTree(final android.net.Uri tree, final Account a, final boolean move) {
        log("[复制] 正在写入 " + a.name + " …");
        pool.execute(new Runnable() {
            public void run() {
                final String out = writeAccountToTree(tree, a.name, a.key.getBytes());
                if (out == null) {
                    runOnUiThread(new Runnable() {
                        public void run() {
                            log("[复制] 失败：写不进这个文件夹，换一个目录或用「导出位置」再试。");
                            toast("复制失败");
                        }
                    });
                    return;
                }
                final boolean removed = move && deleteExportCopy(a);
                runOnUiThread(new Runnable() {
                    public void run() {
                        a.folder = out;
                        saveVault();
                        refreshList();
                        if (move) {
                            log(removed ? ("[移动] 已写入 " + out + "，原导出文件已删除")
                                    : ("[复制] 已写入 " + out + "（原来那份没删掉，可以手动清理）"));
                        } else {
                            log("[复制] 已写入 " + out);
                        }
                        toast(move ? "已移动" : "已复制");
                    }
                });
            }
        });
    }

    private String writeAccountToTree(android.net.Uri tree, String name, byte[] data) {
        try {
            String treeId = android.provider.DocumentsContract.getTreeDocumentId(tree);
            android.net.Uri rootDoc = android.provider.DocumentsContract.buildDocumentUriUsingTree(tree, treeId);
            String safe = safeName(name);
            android.net.Uri sub = findChild(rootDoc, safe);
            if (sub == null) {
                sub = android.provider.DocumentsContract.createDocument(getContentResolver(), rootDoc,
                        "vnd.android.document/directory", safe);
            }
            if (sub == null) return null;
            android.net.Uri old = findChild(sub, "AuthKey.txt");
            if (old != null) {
                try { getContentResolver().delete(old, null, null); } catch (Throwable ignored) { }
            }
            android.net.Uri f = android.provider.DocumentsContract.createDocument(getContentResolver(),
                    sub, "text/plain", "AuthKey.txt");
            if (f == null) return null;
            OutputStream os = getContentResolver().openOutputStream(f);
            os.write(data);
            os.flush();
            os.close();
            return treeLabel(tree) + "/" + safe + "/AuthKey.txt";
        } catch (Throwable t) {
            log("[复制] 写入出错：" + t);
            return null;
        }
    }

    private String treeLabel(android.net.Uri tree) {
        if (tree == null) return "所选文件夹";
        String label = null;
        try {
            label = tree.getLastPathSegment();
            int c = label == null ? -1 : label.indexOf(':');
            if (c >= 0 && c + 1 < label.length()) label = label.substring(c + 1);
        } catch (Throwable ignored) { }
        return label == null || label.length() == 0 ? "所选文件夹" : label;
    }

    /** 账号对应的导出文件（只在能确定是绝对路径时返回）。 */
    private File exportFileOf(Account a) {
        if (a == null || a.folder == null || a.folder.length() == 0) return null;
        if (a.folder.startsWith("/")) return new File(a.folder);
        if (a.folder.startsWith("Download/")) {
            return new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),
                    a.folder.substring("Download/".length()));
        }
        return null;
    }

    private boolean deleteExportCopy(Account a) {
        File f = exportFileOf(a);
        if (f == null) return false;
        try {
            if (f.isFile() && f.delete()) return true;
        } catch (Throwable ignored) { }
        if (hasShell()) {
            Res r = shell("rm -f '" + f.getAbsolutePath() + "'", 8000);
            return r.code == 0;
        }
        return false;
    }

    private void doRename() {
        final Account a = selected();
        if (a == null) {
            toast("请先选中一个账号");
            return;
        }
        if (a.isBackup()) {
            toast("备份不能重命名");
            return;
        }
        final EditText et = new EditText(this);
        et.setInputType(InputType.TYPE_CLASS_TEXT);
        et.setText(a.name);
        new AlertDialog.Builder(this)
                .setTitle("重命名账号")
                .setView(et)
                .setPositiveButton("确定", new android.content.DialogInterface.OnClickListener() {
                    public void onClick(android.content.DialogInterface d, int w) {
                        String n = et.getText().toString().trim();
                        if (n.length() > 0) {
                            a.name = n;
                            saveVault();
                            refreshList();
                        }
                    }
                })
                .setNegativeButton("取消", null)
                .show();
    }

    private void doDelete() {
        final Account a = selected();
        if (a == null) {
            toast("请先选中一个账号");
            return;
        }
        new AlertDialog.Builder(this)
                .setTitle(a.isBackup() ? "删除这条备份" : "删除账号")
                .setMessage("确定删除「" + a.name + "」？" + (a.isBackup() ? "已导出的 AuthKey.txt 不会删。" : "此操作不可撤销。"))
                .setPositiveButton("删除", new android.content.DialogInterface.OnClickListener() {
                    public void onClick(android.content.DialogInterface d, int w) {
                        accounts.remove(a);
                        saveVault();
                        refreshList();
                        log("[删除] 已删除 " + a.name);
                    }
                })
                .setNegativeButton("取消", null)
                .show();
    }

    // ---------- 导出文件夹同步 ----------

    private File exportRootFileDefault() {
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
    }

    private static String readTextFile(File f) {
        FileInputStream in = null;
        try {
            in = new FileInputStream(f);
            byte[] b = new byte[(int) Math.min(f.length(), 65536)];
            int n = in.read(b);
            if (n <= 0) return null;
            return new String(b, 0, n, "UTF-8");
        } catch (Throwable t) {
            return null;
        } finally {
            try { if (in != null) in.close(); } catch (Throwable ignored) { }
        }
    }

    private String readUriText(Uri u) {
        InputStream in = null;
        try {
            in = getContentResolver().openInputStream(u);
            if (in == null) return null;
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            byte[] buf = new byte[4096];
            int n;
            while ((n = in.read(buf)) > 0) bo.write(buf, 0, n);
            return new String(bo.toByteArray(), "UTF-8");
        } catch (Throwable t) {
            return null;
        } finally {
            try { if (in != null) in.close(); } catch (Throwable ignored) { }
        }
    }

    private List<Account> scanExportRoot() {
        List<Account> out = new ArrayList<Account>();
        try {
            File root = exportRootGameDir();
            File[] dirs = root.listFiles();
            if (dirs != null) {
                for (File d : dirs) {
                    if (d == null || !d.isDirectory()) continue;
                    if (d.getName().startsWith("_")) continue;
                    if (d.getName().equals("导入前备份")) continue;
                    File f = new File(d, "AuthKey.txt");
                    if (!f.isFile()) continue;
                    String k = readTextFile(f);
                    if (k == null) continue;
                    k = k.trim();
                    if (k.length() < 8) continue;
                    Account a = new Account(safeName(d.getName()), k);
                    a.game = game.id;
                    a.note = "来自导出文件夹";
                    a.folder = f.getAbsolutePath();
                    out.add(a);
                }
            }
        } catch (Throwable t) {
            log("[账号] 读默认导出文件夹失败：" + t);
        }
        Uri tree = exportTreeForGame();
        if (tree != null) {
            android.database.Cursor c = null;
            try {
                String treeId = android.provider.DocumentsContract.getDocumentId(tree);
                c = getContentResolver().query(
                        android.provider.DocumentsContract.buildChildDocumentsUriUsingTree(tree, treeId),
                        new String[]{android.provider.DocumentsContract.Document.COLUMN_DOCUMENT_ID,
                                android.provider.DocumentsContract.Document.COLUMN_DISPLAY_NAME,
                                android.provider.DocumentsContract.Document.COLUMN_MIME_TYPE}, null, null, null);
                while (c != null && c.moveToNext()) {
                    String mime = c.getString(2);
                    if (mime == null || mime.indexOf("directory") < 0) continue;
                    String nm = c.getString(1);
                    if (nm == null || nm.startsWith("_")) continue;
                    Uri sub = android.provider.DocumentsContract.buildDocumentUriUsingTree(tree, c.getString(0));
                    Uri f = findChild(sub, "AuthKey.txt");
                    if (f == null) continue;
                    String k = readUriText(f);
                    if (k == null) continue;
                    k = k.trim();
                    if (k.length() < 8) continue;
                    Account a = new Account(safeName(nm), k);
                    a.game = game.id;
                    a.note = "来自导出文件夹";
                    a.folder = exportRootLabelFull() + nm + "/AuthKey.txt";
                    out.add(a);
                }
            } catch (Throwable t) {
                log("[账号] 读自定义导出目录失败：" + t);
            } finally {
                try { if (c != null) c.close(); } catch (Throwable ignored) { }
            }
        }
        return out;
    }

    private int syncFromExportFolder() {
        List<Account> found = scanExportRoot();
        exportEntries.clear();
        int changed = 0;
        for (Account f : found) {
            boolean inVault = false;
            for (Account a : accounts) {
                if (inGame(a) && a.key != null && a.key.trim().equals(f.key)) {
                    inVault = true;
                    if (a.folder == null || a.folder.length() == 0 || !a.folder.equals(f.folder)) {
                        a.folder = f.folder;
                        changed++;
                    }
                    break;
                }
            }
            if (!inVault) exportEntries.add(f);
        }
        return exportEntries.size() > 0 ? (exportEntries.size() + changed) : changed;
    }

    private void syncFromExportFolderAsync() {
        pool.execute(new Runnable() {
            public void run() {
                final int n = syncFromExportFolder();
                runOnUiThread(new Runnable() {
                    public void run() {
                        if (n > 0) {
                            saveVault();
                            log("[账号] 从导出文件夹读到 " + n + " 个 key");
                        }
                        refreshList();
                    }
                });
            }
        });
    }

    // ---------- 导入前备份 ----------

    private android.net.Uri backupRootUri() {
        String u = getPreferences(MODE_PRIVATE).getString("backupRoot", "");
        return u.length() == 0 ? null : android.net.Uri.parse(u);
    }

    private String backupRootLabel() {
        String l = getPreferences(MODE_PRIVATE).getString("backupRootLabel", "");
        return l.length() == 0 ? "Download/东放Key/导入前备份/" : l;
    }

    private void chooseBackupDir() {
        try {
            Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
            i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                    | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
            startActivityForResult(i, REQ_TREE_BAK);
        } catch (Throwable t) {
            toast("无法打开文件夹选择器");
        }
    }

    /** 往用户选的备份目录根部写一个文件（读回校验靠调用方的长度/回读逻辑）。 */
    private String writeFileToTreeRoot(android.net.Uri tree, String fileName, byte[] data) {
        try {
            String treeId = android.provider.DocumentsContract.getTreeDocumentId(tree);
            android.net.Uri rootDoc = android.provider.DocumentsContract.buildDocumentUriUsingTree(tree, treeId);
            android.net.Uri old = findChild(rootDoc, fileName);
            if (old != null) {
                try { getContentResolver().delete(old, null, null); } catch (Throwable ignored) { }
            }
            android.net.Uri f = android.provider.DocumentsContract.createDocument(getContentResolver(),
                    rootDoc, "text/plain", fileName);
            if (f == null) return null;
            OutputStream os = getContentResolver().openOutputStream(f);
            os.write(data);
            os.flush();
            os.close();
            return backupRootLabel() + fileName;
        } catch (Throwable t) {
            log("[备份] 自定义目录写入出错：" + t);
            return null;
        }
    }

    private String backupRootPath() {
        return Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS).getAbsolutePath()
                + "/东放Key/导入前备份";
    }

    /** 账号库里是否已经有一份完全相同的自动备份。 */
    private Account findBackupOfKey(String key) {
        if (key == null) return null;
        String k = key.trim();
        for (Account b : accounts) {
            if (b.isBackup() && inGame(b) && !isExportEntry(b) && b.key != null && b.key.trim().equals(k)) return b;
        }
        return null;
    }

    private String lastBackupPath() {
        String p = getPreferences(MODE_PRIVATE).getString("lastBackup", "");
        return p.length() == 0 ? "还没有导入过，导入时会自动备份" : p;
    }

    private String backupCurrentKey(String key, String target) {
        byte[] data = key.getBytes();
        String name = "AuthKey-" + new SimpleDateFormat("MMdd-HHmmss", Locale.US).format(new Date())
                + "-" + hash(key).substring(0, 8) + ".txt";
        android.net.Uri btree = backupRootUri();
        if (btree != null) {
            String t = writeFileToTreeRoot(btree, name, data);
            if (t != null) return t;
            log("[备份] 自定义备份目录写入失败，改用默认目录");
        }
        String rel = "Download/东放Key/导入前备份/" + name;
        String dir = backupRootPath();
        try {
            File d = new File(dir);
            if (d.exists() || d.mkdirs()) {
                File f = new File(d, name);
                FileOutputStream fo = new FileOutputStream(f);
                try {
                    fo.write(data);
                    fo.flush();
                } finally {
                    fo.close();
                }
                if (f.length() == data.length) return rel;
            }
        } catch (Throwable t) {
            log("[备份] 直接写入失败：" + t.getMessage());
        }
        if (Build.VERSION.SDK_INT >= 29) {
            OutputStream os = null;
            try {
                ContentValues cv = new ContentValues();
                cv.put(MediaStore.MediaColumns.DISPLAY_NAME, name);
                cv.put(MediaStore.MediaColumns.MIME_TYPE, "text/plain");
                cv.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/东放Key/导入前备份");
                Uri uri = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, cv);
                if (uri != null) {
                    os = getContentResolver().openOutputStream(uri);
                    if (os != null) {
                        os.write(data);
                        os.flush();
                        return rel;
                    }
                }
            } catch (Throwable t) {
                log("[备份] MediaStore 写入失败：" + t.getMessage());
            } finally {
                try { if (os != null) os.close(); } catch (Throwable ignored) { }
            }
        }
        if (hasShell()) {
            Res r = shWithInput("mkdir -p '" + dir + "' && cat > '" + dir + "/" + name + "'", data, 20000);
            if (r.code == 0) return rel;
        }
        return null;
    }

    // ---------- 免责声明 ----------

    private void maybeShowDisclaimer() {
        if (getPreferences(MODE_PRIVATE).getBoolean("agreed", false)) return;
        showDisclaimer();
    }

    private void showDisclaimer() {
        final LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        final TextView body = new TextView(this);
        body.setTextSize(12);
        body.setTextColor(Color.parseColor("#3A4250"));
        body.setLineSpacing(dp(4), 1f);
        body.setText("免责声明"
                + "\n\n1. 本工具只做一件事：把游戏目录里的 AuthKey 文件复制出来备份，需要时再复制回去。不修改游戏数据、不上传任何内容、不联网（只有「检查更新」会访问 GitHub）。"
                + "\n\n2. AuthKey 等同于账号密码。任何人拿到这个文件，就能直接登录你的账号，而且你无法察觉。请不要把 key 发给别人、发到群里、传到网盘或公开仓库。"
                + "\n\n3. 导入时本工具会先停掉游戏，把游戏里正在用的 key 备份到 Download/东放Key/导入前备份/，再写入你选择的 key。备份文件请自己保管好；换机、重装、清数据前，建议再手动导出一份。"
                + "\n\n4. 导入会覆盖游戏当前登录的账号。如果原 key 没有备份又被覆盖，账号可能无法找回，且本工具无法协助恢复。"
                + "\n\n5. 本工具与 Lifewonders 无任何关系，是非官方第三方工具。使用本工具导致的账号丢失、封禁、数据异常等后果，由使用者自行承担。"
                + "\n\n6. 请勿将本工具用于盗号、买卖或共享账号等违反游戏条款的行为。"
                + "\n\n继续使用即表示你已阅读、理解并接受以上全部内容。");
        final ScrollView sv = new ScrollView(this);
        sv.addView(body);
        box.addView(sv, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(300)));
        final TextView tip = new TextView(this);
        tip.setTextSize(12);
        tip.setTextColor(Color.parseColor("#8A93A0"));
        tip.setPadding(0, dp(10), 0, 0);
        tip.setText("请阅读到最底部，倒计时结束后才能点「同意」");
        box.addView(tip);

        final boolean[] bottom = new boolean[]{false};
        final int[] left = new int[]{10};
        final AlertDialog dlg = new AlertDialog.Builder(this)
                .setTitle("免责声明 · 请先读完")
                .setView(box)
                .setPositiveButton("同意（10）", null)
                .setNegativeButton("退出", null)
                .setCancelable(false)
                .create();
        dlg.setOnShowListener(new android.content.DialogInterface.OnShowListener() {
            public void onShow(android.content.DialogInterface d) {
                final Button ok = dlg.getButton(AlertDialog.BUTTON_POSITIVE);
                ok.setEnabled(false);
                ok.setOnClickListener(new View.OnClickListener() {
                    public void onClick(View v) {
                        getPreferences(MODE_PRIVATE).edit().putBoolean("agreed", true).apply();
                        dlg.dismiss();
                        log("[声明] 已阅读并同意免责声明");
                    }
                });
                dlg.getButton(AlertDialog.BUTTON_NEGATIVE).setOnClickListener(new View.OnClickListener() {
                    public void onClick(View v) {
                        finish();
                    }
                });
                final Handler h = new Handler();
                h.postDelayed(new Runnable() {
                    public void run() {
                        left[0]--;
                        if (left[0] < 0) left[0] = 0;
                        boolean ready = left[0] <= 0 && bottom[0];
                        if (left[0] > 0) {
                            ok.setText("同意（" + left[0] + "）");
                        } else {
                            ok.setText(bottom[0] ? "同意" : "请先读到底部");
                        }
                        ok.setEnabled(ready);
                        if (bottom[0] && left[0] <= 0) {
                            tip.setText("可以点「同意」了");
                        } else if (left[0] > 0 && bottom[0]) {
                            tip.setText("还需等待 " + left[0] + " 秒");
                        } else if (left[0] > 0) {
                            tip.setText("请阅读到最底部，倒计时结束后才能点「同意」（还剩 " + left[0] + " 秒）");
                        } else {
                            tip.setText("请阅读到最底部后才能点「同意」");
                        }
                        if (left[0] > 0) h.postDelayed(this, 1000);
                    }
                }, 1000);
                sv.setOnScrollChangeListener(new View.OnScrollChangeListener() {
                    public void onScrollChange(View v, int sx, int sy, int osx, int osy) {
                        View child = sv.getChildAt(0);
                        if (child == null) return;
                        if (sy + sv.getHeight() >= child.getBottom() - dp(8)) {
                            bottom[0] = true;
                            if (left[0] <= 0) {
                                ok.setEnabled(true);
                                ok.setText("同意");
                                tip.setText("可以点「同意」了");
                            }
                        }
                    }
                });
            }
        });
        dlg.show();
        sv.post(new Runnable() {
            public void run() {
                sv.scrollTo(0, 0);
            }
        });
    }

    private void doImport() {
        final Account a = selected();
        if (a == null) {
            toast("请先选中一个账号");
            return;
        }
        if (!curFpLoaded) {
            pendingImport = a;
            refreshCurrentFp();
            toast("正在读取游戏里正在用的 key…");
            return;
        }
        String now = curFp == null
                ? (curFpLoaded ? "读不到（需要 Shizuku 或 Root 权限）" : "读取中…")
                : curFp;
        boolean same = curFp != null && curFp.equals(a.fpShort());
        String msg = "即将把「" + a.name + "」（指纹 " + a.fpShort() + "）写进「" + game.label + "」，会先强制停止这个游戏。\n\n"
                + "游戏里现在用的：指纹 " + now + "\n\n"
                + "导入前会自动把现在的 key 备份到「备份」分段；万一写入失败，会尝试把原 key 写回去。"
                + (same ? "\n\n注意：这就是游戏里正在用的账号，导入后不会有任何变化。" : "");
        new AlertDialog.Builder(this)
                .setTitle("导入到游戏？")
                .setMessage(msg)
                .setPositiveButton("导入", new android.content.DialogInterface.OnClickListener() {
                    public void onClick(android.content.DialogInterface d, int w) {
                        doImportNow(a);
                    }
                })
                .setNegativeButton("取消", null)
                .show();
    }

    private void doImportNow(final Account a) {
        log("--- 开始导入：" + a.name + " ---");
        pool.execute(new Runnable() {
            public void run() {
                // 1. 备份现有 key
                final boolean[] backupOk = {true};
                String old = null;
                byte[] cur = readKeyAt(EXT_KEY);
                if (cur == null) cur = readKeyAt(PREFS1);
                if (cur != null) {
                    old = new String(cur).trim();
                    if (old.length() >= 8) {
                        Account already = findBackupOfKey(old);
                        if (already != null) {
                            log("[备份] 这个 key 已经备份过（" + already.name + "），跳过重复备份");
                        } else {
                        final String saved = backupCurrentKey(old, a.name);
                        if (saved == null) backupOk[0] = false;
                        final Account bak = new Account("导入前备份 " + stamp(), old);
                        bak.kind = "backup";
                        bak.game = game.id;
                        bak.note = saved == null
                                ? ("导入「" + a.name + "」前自动备份（文件写入失败，只存在账号库）")
                                : ("导入「" + a.name + "」前自动备份 → " + saved);
                        bak.folder = saved == null ? "" : saved;
                        runOnUiThread(new Runnable() {
                            public void run() {
                                accounts.add(bak);
                                saveVault();
                                refreshList();
                                if (saved != null) {
                                    getPreferences(MODE_PRIVATE).edit().putString("lastBackup", saved).apply();
                                }
                            }
                        });
                        log(saved == null
                                ? "[备份] 当前 key 已存进账号库（文件写入失败，请手动导出一次）"
                                : ("[备份] 当前 key 已存到 " + saved));
                        }
                    }
                }
                if (!backupOk[0]) {
                    log("[导入已取消] 备份没能写成文件，为避免覆盖掉现在登录的账号，本次导入已中止。请先检查存储权限与剩余空间，然后再点一次导入。");
                    toast("备份失败，已取消导入");
                    return;
                }
                final String prevKey = old;
                // 2. 停止游戏
                shell("am force-stop " + PKG, 15000);
                log("[停止] 已尝试停止游戏进程");
                // 3. 写入
                boolean ok = writeKey(a.key.getBytes());
                if (!ok) {
                    log("[失败] 写入 AuthKey 失败，正在把原来的 key 写回去…");
                    if (prevKey != null) {
                        boolean restored = writeKey(prevKey.getBytes());
                        log(restored
                                ? "[恢复] 已把原 key 写回，游戏登录状态不变。"
                                : "[恢复] 原 key 写回也失败了，请用「导入前备份」里的文件手动恢复。");
                    }
                    toast("导入失败");
                    return;
                }
                // 4. 校验
                byte[] back = readKeyAt(EXT_KEY);
                String got = back == null ? "" : new String(back).trim();
                if (!got.equals(a.key.trim())) {
                    log("[警告] 回读校验不一致（" + (back == null ? "读不到" : "内容不同") + "），请手动确认。");
                } else {
                    log("[成功] 已导入并校验通过。启动游戏即可登录该账号。");
                }
                runOnUiThread(new Runnable() {
                    public void run() {
                        curFpLoaded = false;
                        refreshCurrentFp();
                        new AlertDialog.Builder(MainActivity.this)
                                .setTitle("导入完成")
                                .setMessage("已写入并校验通过。现在打开游戏就会用「" + a.name + "」登录。")
                                .setPositiveButton("打开游戏", new android.content.DialogInterface.OnClickListener() {
                                    public void onClick(android.content.DialogInterface d, int w) {
                                        launchGame();
                                    }
                                })
                                .setNegativeButton("稍后", null)
                                .show();
                    }
                });
            }
        });
    }

    private boolean writeKey(byte[] data) {
        // 优先 root：写外部目录 + 私有 prefs
        if (hasRoot) {
            File cache = new File(getCacheDir(), "authkey.tmp");
            FileOutputStream fo = null;
            try {
                fo = new FileOutputStream(cache);
                fo.write(data);
                fo.flush();
            } catch (Exception e) {
                log("[err] 写临时文件失败：" + e);
                return false;
            } finally {
                try {
                    if (fo != null) fo.close();
                } catch (Exception ignored) {
                }
            }
            String src = cache.getAbsolutePath();
            su("mkdir -p '" + EXT_DIR + "'", 10000);
            Res r = su("cp '" + src + "' '" + EXT_KEY + "'", 15000);
            if (r.code != 0) {
                log("[err] cp 失败：" + r.err.trim());
            }
            su("chmod 660 '" + EXT_KEY + "' 2>/dev/null; chown $(stat -c %u:%g /data/data/" + PKG + ") '" + EXT_KEY + "' 2>/dev/null", 10000);
            cache.delete();
            byte[] chk = readKeyAt(EXT_KEY);
            if (chk != null && new String(chk).trim().equals(new String(data).trim())) return true;
            log("[root] 外部目录写入未通过校验，尝试私有 prefs …");
            return writePrefs(data, src);
        }
        // Shizuku：以 shell 身份写（等同 adb push），不需要 root
        if (shizukuReady()) {
            File stage = new File(getExternalFilesDir(null), "authkey.tmp");
            FileOutputStream so = null;
            try {
                so = new FileOutputStream(stage);
                so.write(data);
                so.flush();
            } catch (Exception e) {
                log("[err] 写暂存文件失败：" + e);
                return false;
            } finally {
                try {
                    if (so != null) so.close();
                } catch (Exception ignored) {
                }
            }
            shell("mkdir -p '" + EXT_DIR + "'", 10000);
            // 原地覆盖：文件已存在时 `cat >` 会保留原属主与权限（用 cp 会把文件变成 shell 所有，游戏可能读不到）
            String cmd = "if [ -f '" + EXT_KEY + "' ]; then cat > '" + EXT_KEY
                    + "'; else cp '" + stage.getAbsolutePath() + "' '" + EXT_KEY
                    + "' && chmod 660 '" + EXT_KEY + "'; fi";
            Res r = shWithInput(cmd, data, 20000);
            stage.delete();
            if (r.code != 0) log("[err] Shizuku 写入失败：" + r.err.trim());
            byte[] chk = readKeyAt(EXT_KEY);
            if (chk != null && new String(chk).trim().equals(new String(data).trim())) return true;
            log("[Shizuku] 写入未通过回读校验。");
            return false;
        }
        // 免 root（Android 10 及以下）
        File f = new File(EXT_KEY);
        FileOutputStream fo = null;
        try {
            File dir = f.getParentFile();
            if (dir != null && !dir.exists()) dir.mkdirs();
            fo = new FileOutputStream(f);
            fo.write(data);
            fo.flush();
            return true;
        } catch (Exception e) {
            log("[err] 无 root 直写失败：" + e);
            return false;
        } finally {
            try {
                if (fo != null) fo.close();
            } catch (Exception ignored) {
            }
        }
    }

    private boolean writePrefs(byte[] data, String srcFile) {
        Res r = su("ls '" + PREFS1 + "' 2>/dev/null", 8000);
        String prefs = new String(r.out).trim().length() > 0 ? PREFS1 : PREFS2;
        Res cur = su("cat '" + prefs + "' 2>/dev/null", 15000);
        String xml = new String(cur.out);
        if (!xml.contains("<map")) {
            log("[err] 读不到 " + prefs + "，无法保留其它设置，已放弃写 prefs。请把本 key 手动填进外部 AuthKey。");
            return false;
        }
        String val = new String(data).trim()
                .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
        String out;
        java.util.regex.Pattern pat = java.util.regex.Pattern.compile(
                "(&lt;string name=\"AuthKey\"&gt;)(.*?)(&lt;/string&gt;)".replace("&lt;", "<").replace("&gt;", ">"),
                java.util.regex.Pattern.DOTALL);
        java.util.regex.Matcher m = pat.matcher(xml);
        if (m.find()) {
            out = m.replaceFirst(java.util.regex.Matcher.quoteReplacement("<string name=\"AuthKey\">" + val + "</string>"));
        } else {
            out = xml.replace("</map>", "<string name=\"AuthKey\">" + val + "</string></map>");
        }
        File tmp = new File(getCacheDir(), "prefs.tmp");
        FileOutputStream fo = null;
        try {
            fo = new FileOutputStream(tmp);
            fo.write(out.getBytes("UTF-8"));
            fo.flush();
        } catch (Exception e) {
            return false;
        } finally {
            try {
                if (fo != null) fo.close();
            } catch (Exception ignored) {
            }
        }
        String cmd = "cp '" + tmp.getAbsolutePath() + "' '" + prefs + "' && chmod 660 '" + prefs + "'"
                + " && chown $(stat -c %u:%g /data/data/" + PKG + ") '" + prefs + "'";
        Res w = su(cmd, 15000);
        tmp.delete();
        if (w.code != 0) {
            log("[err] 写 prefs 失败：" + w.err.trim());
            return false;
        }
        log("[root] 已写入 " + prefs);
        return true;
    }
}
