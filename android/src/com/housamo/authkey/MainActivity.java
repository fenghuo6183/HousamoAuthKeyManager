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

        /** 导出 / 备份目录里这个游戏用的子文件夹（每个游戏一个同名子目录）。 */
        String exportSub() {
            return label;
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
    static final String CURRENT_VER = "1.0.20";
    static final String UP_API = "https://api.github.com/repos/fenghuo6183/HousamoAuthKeyManager/releases/latest";
    private static File pendingApk = null;
    private String promptedUpdate = "";

    private TextView tvState;
    private LinearLayout host;
    private View pageHome, pageTask, pageAcc, pageSet;
    private TextView tabHome, tabTask, tabAcc, tabSet;
    private Button btnLock, btnShot, btnNight;
    private TextView rowRootVal, rowGameVal, rowShzkVal, rowPermVal, rowCount, rowSaved, rowSelVal;
    private TextView rowStoreVal, rowResVal, rowOsVal, rowVerVal;
    private TextView rowSvcVal, rowModeVal, rowBatteryVal, rowNotifVal, rowGameVerVal, rowExportVal, rowUpdateVal;
    private TextView rowBakVal;
    private static final int REQ_TREE = 0x71;
    private static final int REQ_TREE_COPY = 0x72;
    private static final int REQ_TREE_BAK = 0x73;
    private static final int REQ_TREE_IMPORT = 0x74;
    private static final int REQ_TREE_ZIP = 0x75;
    private static final int REQ_QR_IMG = 0x76;
    private static final int REQ_QR_SHOT = 0x77;
    /** 相机拍照扫二维码时的落盘位置（onActivityResult 里读回来解码）。 */
    private File pendingShot;
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
    private LinearLayout permBox = null;
    private final java.util.List<Button> gameButtons = new java.util.ArrayList<Button>();
    private Account pendingImport = null;
    private boolean curFpBusy = false;
    private boolean curFpLoaded = false;
    private int curPage = 0;
    private TextView rowHomeFp, rowHomeBak, rowHomeCnt;
    private TextView rowKeepVal, rowNightVal, rowLockVal, rowShotVal;
    private boolean unlocked = false;
    private long lastBgAt = 0L;
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
        root.setBackgroundColor(c("#F2F3F6"));
        applyTheme();
        applyShotFlag();

        host = new LinearLayout(this);
        host.setOrientation(LinearLayout.VERTICAL);
        root.addView(host, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));

        pageHome = wrapScroll(buildHome());
        pageTask = wrapScroll(buildTask());
        pageAcc = buildAccounts();
        pageSet = wrapScroll(buildSettings());
        host.addView(pageHome, full());
        host.addView(pageTask, full());
        host.addView(pageAcc, full());
        host.addView(pageSet, full());

        View line = new View(this);
        line.setBackgroundColor(c("#E6E9EF"));
        root.addView(line, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));

        LinearLayout nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        nav.setBackgroundColor(c("#FFFFFF"));
        nav.setPadding(0, dp(6), 0, dp(6));
        tabHome = mkTab("首页", R.drawable.ic_home);
        tabTask = mkTab("任务", R.drawable.ic_task);
        tabAcc = mkTab("账号", R.drawable.ic_acc);
        tabSet = mkTab("设置", R.drawable.ic_set);
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

    private TextView mkTab(String text, int icon) {
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
    }

    private LinearLayout.LayoutParams weightNav() {
        return new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
    }

    /** 给整页套一层滚动容器：内容比屏幕高时可以滑，不会出现「下面那截永远看不见」。 */
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
        int on = c("#2F6BFF");
        int off = c("#9AA3B0");
        TextView[] tabs = new TextView[]{tabHome, tabTask, tabAcc, tabSet};
        for (int i = 0; i < tabs.length; i++) {
            if (tabs[i] == null) continue;
            tabs[i].setTextColor(idx == i ? on : off);
            tabs[i].setTypeface(null, idx == i ? android.graphics.Typeface.BOLD : android.graphics.Typeface.NORMAL);
            if (Build.VERSION.SDK_INT >= 23) {
                tabs[i].setCompoundDrawableTintList(android.content.res.ColorStateList.valueOf(idx == i ? on : off));
            }
        }
        if (idx == 2) {
            curFpLoaded = false;
            refreshCurrentFp();
        }
    }

    // ---------- 主题（浅色 / 深色） ----------

    private boolean night() {
        return getPreferences(MODE_PRIVATE).getBoolean("night", false);
    }

    /** 所有颜色都从这里过一道，深色模式下自动换成暗色。 */
    private int c(String hex) {
        if (!night()) return Color.parseColor(hex);
        String h = hex.toUpperCase(Locale.US);
        if ("#FFFFFF".equals(h)) return Color.parseColor("#171B21");
        if ("#F2F3F6".equals(h)) return Color.parseColor("#0E1116");
        if ("#101418".equals(h)) return Color.parseColor("#E7ECF3");
        if ("#2B3442".equals(h)) return Color.parseColor("#D7DEE8");
        if ("#3B4252".equals(h)) return Color.parseColor("#CFD6E1");
        if ("#5B6470".equals(h) || "#5B6572".equals(h)) return Color.parseColor("#AAB4C2");
        if ("#8A93A0".equals(h) || "#9AA3B0".equals(h)) return Color.parseColor("#8B96A6");
        if ("#EBEEF3".equals(h) || "#EBEFF5".equals(h) || "#EFF1F5".equals(h)) return Color.parseColor("#2A3038");
        if ("#E6E9EF".equals(h) || "#DCE1E8".equals(h) || "#E7EBF2".equals(h) || "#E6EAF1".equals(h)) return Color.parseColor("#2A3038");
        if ("#F2F4F8".equals(h) || "#F3F5F9".equals(h) || "#F5F7FB".equals(h) || "#F7F8FB".equals(h)) return Color.parseColor("#1E242C");
        if ("#F2F6FF".equals(h) || "#EAF0FF".equals(h)) return Color.parseColor("#1B2536");
        if ("#E8F7EF".equals(h)) return Color.parseColor("#16301F");
        if ("#FBF3DA".equals(h)) return Color.parseColor("#2E2716");
        if ("#8A6D1F".equals(h) || "#A3741A".equals(h)) return Color.parseColor("#E3BC63");
        if ("#19A974".equals(h)) return Color.parseColor("#4ADE80");
        if ("#F3B4B6".equals(h)) return Color.parseColor("#7A3B3E");
        int v = Color.parseColor(hex);
        int lum = (Color.red(v) * 299 + Color.green(v) * 587 + Color.blue(v) * 114) / 1000;
        if (lum >= 225) return Color.parseColor("#1A2028");
        if (lum >= 195) return Color.parseColor("#232A34");
        if (lum <= 95) return Color.parseColor("#DCE3EC");
        return v;
    }

    private boolean lockOn() {
        return getPreferences(MODE_PRIVATE).getString("lockPin", "").length() > 0;
    }

    private boolean noShot() {
        return getPreferences(MODE_PRIVATE).getBoolean("noShot", false);
    }

    /** 安全卡片上两行的状态文字 + 按钮文字，状态一变就刷一次。 */
    private void refreshSec() {
        boolean lk = lockOn(), ns = noShot();
        if (rowLockVal != null) rowLockVal.setText(lk ? "已开启：打开 App 要先输密码" : "未开启：打开 App 不需要密码");
        if (btnLock != null) btnLock.setText(lk ? "关闭" : "开启");
        if (rowShotVal != null) rowShotVal.setText(ns ? "已禁止：系统截图和录屏是黑的" : "允许：可以正常截图录屏");
        if (btnShot != null) btnShot.setText(ns ? "关闭" : "开启");
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
            dlgSub(c, "设一个 4-6 位数字密码。之后每次打开 App（或退到后台超过 30 秒回来）都要先输密码。\n\n忘了只能重装 App。");
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
                            refreshSec();
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
                refreshSec();
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
                dlgSub(d, "密码没有后门，本地只存了它的哈希。\n\n唯一的办法是卸载重装 App。你的 key 都在 Download/东放Key/ 里，重装后账号库是空的，但可以从文件夹重新导入，不会丢号。");
                final AlertDialog[] h2 = new AlertDialog[1];
                d.addView(dlgPrimary("知道了", new View.OnClickListener() {
                    public void onClick(View v) { if (h2[0] != null) h2[0].dismiss(); }
                }));
                h2[0] = showCard(d);
            }
        }, false);
        c.addView(row);
        h[0] = showCard(c);
        h[0].setCancelable(false);
        h[0].setCanceledOnTouchOutside(false);
    }

    private void applyTheme() {
        boolean n = night();
        try {
            getWindow().setStatusBarColor(c("#F2F3F6"));
            getWindow().setNavigationBarColor(n ? c("#0E1116") : c("#FFFFFF"));
            if (Build.VERSION.SDK_INT >= 23 && !n) {
                getWindow().getDecorView().setSystemUiVisibility(android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
            } else if (Build.VERSION.SDK_INT >= 23) {
                getWindow().getDecorView().setSystemUiVisibility(0);
            }
        } catch (Throwable ignored) {
        }
    }

    private void toggleNight() {
        getPreferences(MODE_PRIVATE).edit().putBoolean("night", !night()).apply();
        recreate();
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
        t.setTextColor(c("#101418"));
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
        sub.setTextColor(c("#9AA3B0"));
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

        LinearLayout ov = card();
        ov.addView(caption("账号概览"));
        rowHomeFp = value(0, "读取中…");
        ov.addView(rowWith(rowHomeFp, "游戏里现在用的 key", new View.OnClickListener() {
            public void onClick(View v) {
                curFpLoaded = false;
                refreshCurrentFp();
            }
        }));
        ov.addView(divider());
        rowHomeBak = value(0, "—");
        ov.addView(rowWith(rowHomeBak, "上次自动备份", null));
        ov.addView(divider());
        rowHomeCnt = value(0, "—");
        ov.addView(rowWith(rowHomeCnt, "账号库", new View.OnClickListener() {
            public void onClick(View v) { showPage(2); }
        }));
        p.addView(ov, cardParams(0));

        LinearLayout mode = card();
        rowModeVal = value(0, "检测中...");
        mode.addView(rowWith(rowModeVal, "运行模式", null));
        TextView mh = new TextView(this);
        mh.setText("免 root 时走 Shizuku shell，有 root 时优先 root。");
        mh.setTextSize(11);
        mh.setTextColor(c("#9AA3B0"));
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

        TextView permTip = new TextView(this);
        permTip.setText("没有 root 也没装 Shizuku？点上面「Shizuku 权限」有图文步骤；不想装任何东西，就用电脑 + USB 线，提取和导入都在 Windows 版里做。");
        permTip.setTextSize(11);
        permTip.setTextColor(c("#8A93A0"));
        permTip.setPadding(dp(4), 0, dp(4), dp(10));
        p.addView(permTip);

        fillDeviceInfo();

        TextView more = new TextView(this);
        more.setText("提取 / 导入 / 导出 / 运行日志 都在「任务」页");
        more.setTextSize(11);
        more.setTextColor(c("#9AA3B0"));
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
        sub.setTextColor(c("#9AA3B0"));
        sub.setPadding(dp(2), 0, 0, dp(8));
        p.addView(sub);
        p.addView(gameSwitcherCard(true), cardParams(0));

        permBox = new LinearLayout(this);
        permBox.setOrientation(LinearLayout.VERTICAL);
        permBox.setVisibility(android.view.View.GONE);
        p.addView(permBox);

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
        ch.setTextColor(c("#9AA3B0"));
        ch.setPadding(dp(2), dp(2), 0, dp(4));
        cur.addView(ch);
        p.addView(cur, cardParams(0));

        p.addView(taskCard("提取当前账号的 key", "把游戏里正在登录的账号 key 抽出来存进账号库，并自动存一份到「设置 → 导出位置」的文件夹。", new View.OnClickListener() {
            public void onClick(View v) { doExtract(); }
        }), cardParams(0));

        p.addView(taskCard("把选中的 key 复制到其他文件夹", "复制一份到你指定的文件夹（备份到别处、发给另一台设备都行）；选「移动」的话，复制完会把原来导出文件夹里的那份删掉。", new View.OnClickListener() {
            public void onClick(View v) { startCopyMove(); }
        }), cardParams(0));

        p.addView(taskCard("从一个文件夹导入 key", "选一个文件夹，把它（含子文件夹）里的 AuthKey 全部加进账号库，只是进「账号」分段，不会碰游戏里现在登录的账号。", new View.OnClickListener() {
            public void onClick(View v) { startImportFolder(); }
        }), cardParams(0));

        p.addView(taskCard("从剪贴板导入 key", "先把 key（或整段 playerprefs xml）复制到剪贴板，点这里取出来存进账号库，不碰游戏。", new View.OnClickListener() {
            public void onClick(View v) { importFromClipboard(); }
        }), cardParams(0));

        p.addView(taskCard("扫一扫二维码", "打开相机对准别的屏幕或纸上的二维码，解出 key 存进账号库；相机打不开时会改用相册选图。", new View.OnClickListener() {
            public void onClick(View v) { pickQrShot(); }
        }), cardParams(0));

        p.addView(taskCard("从相册选二维码", "二维码是截图或图片时，从相册 / 文件里选那张图识别，不调相机。", new View.OnClickListener() {
            public void onClick(View v) { pickQrImage(); }
        }), cardParams(0));

        p.addView(taskCard("打包导出全部 key", "选一个文件夹，把账号库里这个游戏的 key 全打成一个 zip（含 manifest），换机备份一次带走。", new View.OnClickListener() {
            public void onClick(View v) { startZipExport(); }
        }), cardParams(0));

        LinearLayout lg = card();
        lg.addView(caption("运行日志"));
        logScroll = new ScrollView(this);
        tvLog = new TextView(this);
        tvLog.setTextSize(11);
        tvLog.setTextColor(c("#5B6470"));
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
        t.setTextColor(c("#101418"));
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
        d.setTextColor(c("#8A93A0"));
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
        tvState.setTextColor(c("#8A93A0"));
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
        rf.addView(divider());
        rf.addView(rowWith(value(0, "选一个文件夹，批量加进账号库"), "从文件夹导入 key", new View.OnClickListener() {
            public void onClick(View v) { startImportFolder(); }
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
        emptyHint.setTextColor(c("#9AA3B0"));
        emptyHint.setGravity(Gravity.CENTER);
        emptyHint.setPadding(dp(24), dp(10), dp(24), dp(10));
        android.widget.FrameLayout.LayoutParams ep = new android.widget.FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT, Gravity.CENTER);
        listWrap.addView(emptyHint, ep);
        p.addView(listWrap, cardParams(1));

        LinearLayout op = card();
        tvAccHint = new TextView(this);
        tvAccHint.setTextSize(11);
        tvAccHint.setTextColor(c("#9AA3B0"));
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
        }));
        p.addView(perm, cardParams(0));

        LinearLayout look = card();
        look.addView(caption("外观"));
        rowNightVal = value(0, night() ? "当前是深色配色" : "当前是浅色配色");
        btnNight = mkBtn(night() ? "切到浅色" : "切到深色", true);
        look.addView(rowWithButtonObj(rowNightVal, "深色模式", btnNight, new View.OnClickListener() {
            public void onClick(View v) { toggleNight(); }
        }));
        TextView lh = new TextView(this);
        lh.setText("深色模式只是换个配色，读写行为完全一样。");
        lh.setTextSize(11);
        lh.setTextColor(c("#9AA3B0"));
        lh.setPadding(dp(2), dp(10), dp(2), dp(2));
        look.addView(lh);
        p.addView(look, cardParams(0));

        LinearLayout sec = card();
        sec.addView(caption("安全"));
        rowLockVal = value(0, "");
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
        refreshSec();
        TextView sech = new TextView(this);
        sech.setText("应用锁是 4-6 位数字密码，忘了只能重装 App（账号文件仍在 Download，不会丢）。防止截屏打开后，系统截图和录屏都会是黑的。");
        sech.setTextSize(11);
        sech.setTextColor(c("#9AA3B0"));
        sech.setPadding(dp(2), dp(10), dp(2), dp(2));
        sec.addView(sech);
        p.addView(sec, cardParams(0));

        LinearLayout exp = card();
        exp.addView(caption("存储位置"));
        rowExportVal = value(0, exportRootLabelFull());
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
        sh.setText("备份位置是每次导入前，自动把游戏里正在用的 key 存一份的地方。不换就存在 " + backupDefaultLabel() + "。");
        sh.setTextSize(11);
        sh.setTextColor(c("#9AA3B0"));
        sh.setPadding(dp(2), dp(10), dp(2), dp(2));
        exp.addView(sh);
        p.addView(exp, cardParams(0));

        LinearLayout bh = card();
        bh.addView(caption("备份与历史"));
        rowKeepVal = value(0, keepLabel(backupKeep()));
        bh.addView(rowWith(rowKeepVal, "自动备份保留", new View.OnClickListener() {
            public void onClick(View v) { chooseBackupKeep(); }
        }));
        bh.addView(divider());
        bh.addView(rowWith(value(0, "手机和电脑同一个 WiFi"), "局域网传输", new View.OnClickListener() {
            public void onClick(View v) { showLanTransfer(); }
        }));
        bh.addView(divider());
        bh.addView(rowWith(value(0, "看每一次导入前的 key"), "导入历史", new View.OnClickListener() {
            public void onClick(View v) { showImportHistory(); }
        }));
        TextView bhh = new TextView(this);
        bhh.setText("自动备份是每次导入前，把游戏里正在用的 key 存下的那一份。默认全部保留。");
        bhh.setTextSize(11);
        bhh.setTextColor(c("#9AA3B0"));
        bhh.setPadding(dp(2), dp(10), dp(2), dp(2));
        bh.addView(bhh);
        p.addView(bh, cardParams(0));

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
        url.setTextColor(c("#2F6BFF"));
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
        note.setTextColor(c("#9AA3B0"));
        note.setPadding(dp(2), dp(10), 0, 0);
        about.addView(note);
        p.addView(about, cardParams(0));

        Button bClear = mkBtn("清空账号库", false);
        bClear.setTextColor(c("#E5484D"));
        bClear.setBackground(roundRect(c("#FFFFFF"), 10, c("#F3B4B6"), 1));
        bClear.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                LinearLayout c = dlgCard();
                dlgTitle(c, "清空账号库");
                dlgSub(c, "会删除本机保存的所有账号记录。各账号导出到 Download 的 AuthKey.txt 不会删。");
                final AlertDialog[] h = new AlertDialog[1];
                c.addView(dlgPrimary("清空", new View.OnClickListener() {
                    public void onClick(View v) {
                        accounts.clear();
                        saveVault();
                        refreshList();
                        log("[库] 已清空账号库");
                        if (h[0] != null) h[0].dismiss();
                    }
                }));
                LinearLayout row = dlgBtnRow();
                dlgAddGhost(row, "取消", new View.OnClickListener() {
                    public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
                }, false);
                c.addView(row);
                h[0] = showCard(c);
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
            box.setBackground(roundRect(on ? c("#F2F6FF") : c("#FFFFFF"),
                    12, on ? c("#AFC7FF") : c("#EBEFF5"), 1));

            LinearLayout col = new LinearLayout(MainActivity.this);
            col.setOrientation(LinearLayout.VERTICAL);

            TextView name = new TextView(MainActivity.this);
            name.setText(a.isBackup() ? a.name.replace("导入前备份", "备份") : a.name);
            name.setTextSize(15);
            name.setSingleLine(true);
            name.setEllipsize(android.text.TextUtils.TruncateAt.END);
            name.setTextColor(c("#101418"));
            name.setTypeface(null, android.graphics.Typeface.BOLD);

            TextView meta = new TextView(MainActivity.this);
            meta.setText(a.isBackup()
                    ? ("指纹 " + a.fpShort() + "  ·  " + a.sizeText() + "  ·  原 key 副本")
                    : ("指纹 " + a.fpShort() + "  ·  " + a.sizeText() + "  ·  " + a.created));
            meta.setTextSize(11);
            meta.setTextColor(c(a.isBackup() ? "#A3741A" : "#5B6572"));
            meta.setPadding(0, dp(3), 0, 0);

            TextView path = new TextView(MainActivity.this);
            boolean exported = a.folder != null && a.folder.length() > 0;
            path.setText(exported ? a.folder
                    : (a.isBackup() ? "只在账号库里，还没写成文件" : expectedPath(a.name) + "（未导出）"));
            path.setTextSize(10);
            path.setSingleLine(true);
            path.setEllipsize(android.text.TextUtils.TruncateAt.END);
            path.setTextColor(c("#9AA3B0"));
            path.setPadding(0, dp(3), 0, 0);

            col.addView(name);
            col.addView(meta);
            col.addView(path);
            String nnote = a.note == null ? "" : a.note.trim();
            if (nnote.length() > 0 && !nnote.startsWith("来源：") && !nnote.startsWith("从文件夹导入：")
                    && !nnote.startsWith("导入「") && !nnote.startsWith("导入到「")) {
                TextView nt = new TextView(MainActivity.this);
                nt.setText("备注 " + nnote);
                nt.setTextSize(11);
                nt.setSingleLine(true);
                nt.setEllipsize(android.text.TextUtils.TruncateAt.END);
                nt.setTextColor(c("#5B6572"));
                nt.setPadding(0, dp(3), 0, 0);
                col.addView(nt);
            }

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
            dot.setBackground(roundRect(on ? c("#2F6BFF") : c("#E6EAF1"), 20, 0, 0));
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
        v.setTextColor(c("#8A93A0"));
        return v;
    }

    /** 一行：左边标题 + 右边一个明显的「更改」按钮，路径显示在下面一行。 */
    private LinearLayout rowWithButton(TextView val, String label, String btnText, View.OnClickListener click) {
        return rowWithButtonObj(val, label, mkBtn(btnText, true), click);
    }

    /** 和 rowWithButton 一样，但按钮由调用方给，方便之后改字（开启/关闭）。 */
    private LinearLayout rowWithButtonObj(TextView val, String label, Button b, View.OnClickListener click) {
        LinearLayout r = new LinearLayout(this);
        r.setOrientation(LinearLayout.VERTICAL);
        r.setPadding(dp(2), dp(12), dp(2), dp(12));
        LinearLayout top = new LinearLayout(this);
        top.setOrientation(LinearLayout.HORIZONTAL);
        top.setGravity(Gravity.CENTER_VERTICAL);
        TextView l = new TextView(this);
        l.setText(label);
        l.setTextSize(14);
        l.setTextColor(c("#1B1F24"));
        top.addView(l, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
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
        l.setTextColor(c("#1B1F24"));
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
        v.setBackgroundColor(c("#EFF1F5"));
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
        c.setBackground(roundRect(c("#FFFFFF"), 16, c("#EBEEF3"), 1));
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
        t.setTextColor(c("#9AA3B0"));
        t.setPadding(dp(2), dp(10), 0, dp(2));
        return t;
    }

    private Button mkBtn(String text, boolean primary) {
        Button b = new Button(this);
        b.setText(text);
        b.setAllCaps(false);
        b.setTextSize(13);
        b.setTextColor(primary ? Color.WHITE : c("#2B3442"));
        if (primary) {
            b.setBackground(roundRect(c("#2F6BFF"), 10, 0, 0));
        } else {
            b.setBackground(roundRect(c("#FFFFFF"), 10, c("#DCE1E8"), 1));
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
        refreshHomeOverview();
        boolean gameInstalled = isInstalled(PKG);
        boolean alive = shizukuAlive();
        boolean granted = alive && shizukuGrantedNow();
        int okColor = c("#2F6BFF");
        int noColor = c("#E5484D");
        int grayColor = c("#8A93A0");
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
        if (rowCount != null) rowCount.setText(countAccounts() + " 个账号 · " + (countBackups() + countExportEntries()) + " 个备份");
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
        refreshPermGuide();
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
                LinearLayout c = dlgCard();
                dlgTitle(c, "还没装 Shizuku");
                dlgSub(c, "Shizuku 能把 adb 权限借给本应用，让 Android 11+ 不用 root 也能读写游戏目录。装好后打开它，按提示用「无线调试」启动，再回这里点「Shizuku 权限」授权。");
                final AlertDialog[] h = new AlertDialog[1];
                c.addView(dlgPrimary("去下载 Shizuku", new View.OnClickListener() {
                    public void onClick(View v) {
                        if (h[0] != null) h[0].dismiss();
                        openUrl("https://github.com/RikkaApps/Shizuku/releases/latest");
                    }
                }));
                LinearLayout row = dlgBtnRow();
                dlgAddGhost(row, "取消", new View.OnClickListener() {
                    public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
                }, false);
                c.addView(row);
                h[0] = showCard(c);
                return;
            }
            log("[Shizuku] 已安装但服务未运行，请先启动 Shizuku。");
            LinearLayout c = dlgCard();
            dlgTitle(c, "Shizuku 还没启动");
            dlgSub(c, "打开 Shizuku 后按它的提示启动服务（手机重启后要重新启动一次），再回这里点「刷新」或「Shizuku 权限」。");
            final AlertDialog[] h = new AlertDialog[1];
            c.addView(dlgPrimary("打开 Shizuku", new View.OnClickListener() {
                public void onClick(View v) {
                    if (h[0] != null) h[0].dismiss();
                    Intent i = getPackageManager().getLaunchIntentForPackage("moe.shizuku.privileged.api");
                    if (i != null) startActivity(i);
                    else openUrl("https://github.com/RikkaApps/Shizuku/releases/latest");
                }
            }));
            LinearLayout row = dlgBtnRow();
            dlgAddGhost(row, "取消", new View.OnClickListener() {
                public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
            }, false);
            c.addView(row);
            h[0] = showCard(c);
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
        t.setTextColor(c("#101418"));
        t.setTypeface(null, android.graphics.Typeface.BOLD);
        c.addView(t);
        TextView d = new TextView(this);
        d.setText("Android 11 以后，手机不让普通 App 直接读别的 App 的数据目录，所以要先“借”一个 shell 权限。下面两种方式任选一种，弄好之后这张卡会自动消失。");
        d.setTextSize(12);
        d.setTextColor(c("#8A93A0"));
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
        t.setTextColor(c("#101418"));
        t.setTypeface(null, android.graphics.Typeface.BOLD);
        box.addView(t);
        TextView d = new TextView(this);
        d.setText(desc);
        d.setTextSize(12);
        d.setTextColor(c("#8A93A0"));
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

    // ---------- 好看点的弹窗 ----------

    private LinearLayout dlgCard() {
        LinearLayout c = new LinearLayout(this);
        c.setOrientation(LinearLayout.VERTICAL);
        c.setBackground(roundRect(c("#FFFFFF"), 20, 0, 0));
        c.setPadding(dp(20), dp(20), dp(20), dp(14));
        return c;
    }

    private void dlgTitle(LinearLayout c, String title) {
        TextView t = new TextView(this);
        t.setText(title);
        t.setTextSize(17);
        t.setTextColor(c("#101418"));
        t.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        c.addView(t);
    }

    private void dlgSub(LinearLayout c, String text) {
        TextView t = new TextView(this);
        t.setText(text);
        t.setTextSize(12.5f);
        t.setTextColor(c("#6B7280"));
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
        n.setBackground(roundRect(c("#2F6BFF"), 11, 0, 0));
        LinearLayout.LayoutParams np = new LinearLayout.LayoutParams(dp(22), dp(22));
        np.rightMargin = dp(10);
        row.addView(n, np);
        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        TextView h = new TextView(this);
        h.setText(head);
        h.setTextSize(13.5f);
        h.setTextColor(c("#101418"));
        h.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        col.addView(h);
        TextView b = new TextView(this);
        b.setText(body);
        b.setTextSize(12.5f);
        b.setTextColor(c("#6B7280"));
        b.setLineSpacing(dp(3), 1.0f);
        b.setPadding(0, dp(3), 0, 0);
        col.addView(b);
        row.addView(col, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0f));
        return row;
    }

    private View dlgOption(String title, String desc, View.OnClickListener click) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setBackground(roundRect(c("#F5F7FB"), 14, c("#E7EBF2"), 1));
        box.setPadding(dp(14), dp(12), dp(14), dp(12));
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        bp.topMargin = dp(10);
        box.setLayoutParams(bp);
        TextView t = new TextView(this);
        t.setText(title);
        t.setTextSize(13.5f);
        t.setTextColor(c("#101418"));
        t.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        box.addView(t);
        TextView d = new TextView(this);
        d.setText(desc);
        d.setTextSize(12.5f);
        d.setTextColor(c("#6B7280"));
        d.setLineSpacing(dp(3), 1.0f);
        d.setPadding(0, dp(4), 0, dp(8));
        box.addView(d);
        TextView go = new TextView(this);
        go.setText("怎么弄  →");
        go.setTextSize(12.5f);
        go.setTextColor(c("#2F6BFF"));
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
        b.setTextColor(c(blue ? "#2F6BFF" : "#6B7280"));
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
        t.setTextColor(c("#3B4252"));
        t.setBackground(roundRect(c("#F2F4F8"), 10, 0, 0));
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

    private LinearLayout dlgBtnRow() {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setPadding(0, dp(6), 0, 0);
        return row;
    }

    private void dlgAddGhost(LinearLayout row, String text, View.OnClickListener click, boolean blue) {
        row.addView(dlgGhost(text, click, blue), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0f));
    }

    private EditText dlgInput(String def) {
        EditText et = new EditText(this);
        et.setText(def);
        et.setSingleLine(true);
        et.setInputType(InputType.TYPE_CLASS_TEXT);
        et.setTextSize(14);
        et.setTextColor(c("#101418"));
        et.setPadding(dp(12), dp(10), dp(12), dp(10));
        et.setBackground(roundRect(c("#F5F7FB"), 12, c("#E7EBF2"), 1));
        et.setSelection(et.getText().length());
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        p.topMargin = dp(14);
        et.setLayoutParams(p);
        return et;
    }

    private View dlgMenuItem(String title, String desc, boolean danger, View.OnClickListener click) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setBackground(roundRect(c("#F7F8FB"), 14, 0, 0));
        box.setPadding(dp(14), dp(12), dp(14), dp(12));
        box.setClickable(true);
        box.setOnClickListener(click);
        TextView t = new TextView(this);
        t.setText(title);
        t.setTextSize(14);
        t.setTextColor(c(danger ? "#E5484D" : "#101418"));
        box.addView(t);
        if (desc != null && desc.length() > 0) {
            TextView d = new TextView(this);
            d.setText(desc);
            d.setTextSize(11.5f);
            d.setTextColor(c("#8A93A0"));
            d.setPadding(0, dp(3), 0, 0);
            box.addView(d);
        }
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        p.topMargin = dp(10);
        box.setLayoutParams(p);
        return box;
    }

    private void startTreePick() {
        try {
            Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
            i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                    | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
            startActivityForResult(i, REQ_TREE_COPY);
        } catch (Throwable t) {
            toast("无法打开文件夹选择器");
        }
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
        codeHint.setTextColor(c("#6B7280"));
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

    private void copyText(String s) {
        try {
            ClipboardManager cm = (ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
            cm.setPrimaryClip(android.content.ClipData.newPlainText("AuthKey", s));
        } catch (Throwable ignored) {
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
            b.setBackground(roundRect(c("#2F6BFF"), 10, 0, 0));
        } else {
            b.setTextColor(c("#5B6572"));
            b.setBackground(roundRect(c("#F3F5F9"), 10, 0, 0));
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
        if (!permReady()) { showNoPerm(); return; }
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
    /** 任务页：把剪贴板里的 key（或整段 xml）存进账号库。 */
    private void importFromClipboard() {
        String text = "";
        try {
            android.content.ClipboardManager cm = (android.content.ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
            if (cm != null && cm.hasPrimaryClip() && cm.getPrimaryClip() != null) {
                android.content.ClipData cd = cm.getPrimaryClip();
                if (cd.getItemCount() > 0 && cd.getItemAt(0).coerceToText(this) != null) {
                    text = cd.getItemAt(0).coerceToText(this).toString().trim();
                }
            }
        } catch (Throwable ignored) {
        }
        if (text.length() == 0) {
            toast("剪贴板是空的");
            return;
        }
        if (text.contains("<string") && text.contains("AuthKey")) {
            String k = extractFromPrefs(text);
            if (k != null && k.trim().length() > 0) text = k.trim();
        }
        if (!isKeyLike(text)) {
            LinearLayout c = dlgCard();
            dlgTitle(c, "剪贴板里这段不像 key");
            dlgSub(c, "key 一般是一长串字母数字。你复制的内容有 " + text.length() + " 个字符"
                    + (text.length() > 120 ? "（可能是网页或说明文字）" : "") + "。\n\n请只复制 AuthKey 那一行，再点一次。");
            final AlertDialog[] h = new AlertDialog[1];
            c.addView(dlgPrimary("知道了", new View.OnClickListener() {
                public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
            }));
            h[0] = showCard(c);
            return;
        }
        if (libraryHasKey(text)) toast("这个 key 账号库里已经有了");
        askNameThenSave(text, "剪贴板");
    }

    /** 账号页长按菜单：只改备注。 */
    private void doEditNote() {
        final Account a = selected();
        if (a == null) {
            toast("请先选中一个账号");
            return;
        }
        LinearLayout c = dlgCard();
        dlgTitle(c, "备注");
        dlgSub(c, "写给自己看的说明，比如「日服小号」「朋友的号」。只存在这台手机上，不影响 key。");
        final EditText et = dlgInput(a.note == null ? "" : a.note);
        c.addView(et);
        final AlertDialog[] h = new AlertDialog[1];
        c.addView(dlgPrimary("保存", new View.OnClickListener() {
            public void onClick(View v) {
                a.note = et.getText().toString().trim();
                saveVault();
                refreshAccountsView();
                refreshList();
                log("[备注] " + a.name + " → " + (a.note.length() == 0 ? "（清空）" : a.note));
                if (h[0] != null) h[0].dismiss();
            }
        }));
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "取消", new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
        }, false);
        c.addView(row);
        h[0] = showCard(c);
    }

    /** 首页「账号概览」三行。 */
    private void refreshHomeOverview() {
        if (rowHomeFp != null) {
            rowHomeFp.setText(curFp != null ? curFp : (curFpLoaded ? "读不到" : "读取中…"));
            rowHomeFp.setTextColor(curFp != null ? c("#2F6BFF") : c("#8A93A0"));
        }
        if (rowHomeBak != null) {
            String lb = getPreferences(MODE_PRIVATE).getString("lastBackup", "");
            String nm = lb;
            if (lb.length() > 0) {
                String[] parts = lb.split("/");
                if (parts.length >= 2) nm = parts[parts.length - 2];
                else if (parts.length == 1) nm = parts[0];
            }
            rowHomeBak.setText(nm.length() == 0 ? "还没有备份" : nm);
        }
        if (rowHomeCnt != null) {
            rowHomeCnt.setText(countAccounts() + " 个账号 · " + (countBackups() + countExportEntries()) + " 个备份");
        }
    }

    private void askNameThenSave(final String key, final String source) {
        final String defName = "设备 " + Build.MODEL + " " + stamp();
        LinearLayout c = dlgCard();
        dlgTitle(c, "给这个账号取个名字");
        dlgSub(c, "会同时导出到 手机存储/" + Environment.DIRECTORY_DOWNLOADS + "/东放Key/" + game.exportSub() + "/<名字>/AuthKey.txt");
        final EditText et = dlgInput(defName);
        c.addView(et);
        final AlertDialog[] h = new AlertDialog[1];
        c.addView(dlgPrimary("保存", new View.OnClickListener() {
            public void onClick(View v) {
                String n = et.getText().toString().trim();
                if (h[0] != null) h[0].dismiss();
                addAccount(n.length() > 0 ? n : defName, key, source);
            }
        }));
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "用默认名", new View.OnClickListener() {
            public void onClick(View v) {
                if (h[0] != null) h[0].dismiss();
                addAccount(defName, key, source);
            }
        }, false);
        c.addView(row);
        h[0] = showCard(c);
    }

    /** 用 MediaStore / 文件系统查 <默认导出根>/[游戏名/]<名字>/AuthKey.txt 是否已存在。 */
    private boolean exportedExists(String name) {
        String safe = safeName(name);
        java.util.List<String> prefixes = new ArrayList<String>();
        prefixes.add(Environment.DIRECTORY_DOWNLOADS + "/东放Key/" + game.exportSub() + "/" + safe + "/");
        // 东放老版本把账号文件夹直接放在 东放Key/ 下，老文件也要认。
        if ("housamo".equals(game.id)) prefixes.add(Environment.DIRECTORY_DOWNLOADS + "/东放Key/" + safe + "/");
        if (android.os.Build.VERSION.SDK_INT >= 29) {
            for (String p : prefixes) {
                android.database.Cursor c = null;
                try {
                    android.net.Uri uri = android.provider.MediaStore.Downloads.EXTERNAL_CONTENT_URI;
                    String[] proj = new String[]{android.provider.MediaStore.Downloads._ID};
                    String sel = android.provider.MediaStore.Downloads.RELATIVE_PATH + " LIKE ? AND "
                            + android.provider.MediaStore.Downloads.DISPLAY_NAME + " = ?";
                    String[] args = new String[]{p + "%", "AuthKey.txt"};
                    c = getContentResolver().query(uri, proj, sel, args, null);
                    if (c != null && c.getCount() > 0) return true;
                } catch (Throwable ignored) {
                } finally {
                    if (c != null) try { c.close(); } catch (Throwable ignored) {}
                }
            }
        }
        for (String p : prefixes) {
            try {
                File f = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),
                        p.substring(Environment.DIRECTORY_DOWNLOADS.length() + 1) + "AuthKey.txt");
                if (f.exists()) return true;
            } catch (Throwable ignored) {
            }
        }
        return false;
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

    // ================= 从一个文件夹批量导入 key 到账号库 =================

    private static class FoundKey {
        String name;
        String key;
        String path;

        FoundKey(String n, String k, String p) {
            name = n;
            key = k;
            path = p;
        }
    }

    private void startImportFolder() {
        Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        try {
            startActivityForResult(i, REQ_TREE_IMPORT);
        } catch (Throwable t) {
            toast("这台手机没有可用的文件选择器");
        }
    }

    private void scanFolderForKeys(final android.net.Uri tree) {
        final String rootLabel = treeLabel(tree);
        log("[导入] 开始扫描：" + rootLabel + "/");
        toast("正在扫描文件夹…");
        pool.execute(new Runnable() {
            public void run() {
                final java.util.List<FoundKey> found = new java.util.ArrayList<FoundKey>();
                try {
                    String rootId = android.provider.DocumentsContract.getTreeDocumentId(tree);
                    walkTreeForKeys(tree, rootId, "", 0, found);
                } catch (Throwable t) {
                    log("[导入] 文件选择器读取失败：" + t);
                }
                if (found.isEmpty()) {
                    String rel = relPathOfTree(tree);
                    if (rel != null) {
                        try {
                            fileWalkForKeys(rel, found);
                            if (!found.isEmpty()) log("[导入] 已改用存储路径扫描：" + rel);
                        } catch (Throwable t) {
                            log("[导入] 存储路径扫描失败：" + t);
                        }
                    }
                }
                log("[导入] 扫描完成，找到 " + found.size() + " 个 key");
                runOnUiThread(new Runnable() {
                    public void run() {
                        showImportFolderResult(tree, rootLabel, found);
                    }
                });
            }
        });
    }

    private void walkTreeForKeys(android.net.Uri tree, String docId, String path, int depth,
                                 java.util.List<FoundKey> out) {
        if (depth > 4 || out.size() >= 80) return;
        android.database.Cursor c = null;
        try {
            android.net.Uri children = android.provider.DocumentsContract.buildChildDocumentsUriUsingTree(tree, docId);
            c = getContentResolver().query(children, new String[]{
                    android.provider.DocumentsContract.Document.COLUMN_DOCUMENT_ID,
                    android.provider.DocumentsContract.Document.COLUMN_DISPLAY_NAME,
                    android.provider.DocumentsContract.Document.COLUMN_MIME_TYPE
            }, null, null, null);
            if (c == null) return;
            while (c.moveToNext()) {
                if (out.size() >= 80) break;
                String id = c.getString(0);
                String nm = c.getString(1);
                String mime = c.getString(2);
                if (id == null || nm == null) continue;
                if (android.provider.DocumentsContract.Document.MIME_TYPE_DIR.equals(mime)) {
                    walkTreeForKeys(tree, id, path + nm + "/", depth + 1, out);
                } else {
                    String key = readKeyDoc(android.provider.DocumentsContract.buildDocumentUriUsingTree(tree, id));
                    if (!isKeyLike(key)) continue;
                    String nmLow = nm.toLowerCase();
                    // 只收像 key 的文件：名字里带 authkey / key，或者短小的 txt / 无扩展名文件
                    boolean nameOk = nmLow.contains("authkey") || nmLow.contains("key")
                            || nmLow.endsWith(".txt") || nmLow.indexOf('.') < 0;
                    if (!nameOk) continue;
                    out.add(new FoundKey(folderLabelOf(path, nm), key.trim(), path + nm));
                }
            }
        } catch (Throwable t) {
            log("[导入] 读取目录失败：" + t);
        } finally {
            try { if (c != null) c.close(); } catch (Throwable ignored) { }
        }
    }

    /** 把 SAF 的 tree uri 换成 /sdcard 下的相对路径，失败返回 null。 */
    private String relPathOfTree(android.net.Uri tree) {
        try {
            String docId = android.provider.DocumentsContract.getTreeDocumentId(tree);
            if (docId == null) return null;
            int c = docId.indexOf(':');
            if (c < 0) return null;
            String vol = docId.substring(0, c);
            String rest = docId.substring(c + 1);
            if (!"primary".equals(vol)) return null;
            return rest;
        } catch (Throwable t) {
            return null;
        }
    }

    private void fileWalkForKeys(String rel, java.util.List<FoundKey> out) {
        File root = new File(Environment.getExternalStorageDirectory(), rel);
        fileWalkDir(root, "", 0, out);
    }

    private void fileWalkDir(File dir, String path, int depth, java.util.List<FoundKey> out) {
        if (dir == null || depth > 4 || out.size() >= 80) return;
        File[] kids = dir.listFiles();
        if (kids == null) return;
        java.util.Arrays.sort(kids);
        for (int i = 0; i < kids.length; i++) {
            if (out.size() >= 80) break;
            File f = kids[i];
            String nm = f.getName();
            if (f.isDirectory()) {
                if (nm.startsWith(".")) continue;
                fileWalkDir(f, path + nm + "/", depth + 1, out);
            } else {
                String nmLow = nm.toLowerCase();
                boolean nameOk = nmLow.contains("authkey") || nmLow.contains("key")
                        || nmLow.endsWith(".txt") || nmLow.indexOf('.') < 0;
                if (!nameOk) continue;
                if (f.length() < 16 || f.length() > 32768) continue;
                String key = readKeyFile(f);
                if (!isKeyLike(key)) continue;
                out.add(new FoundKey(folderLabelOf(path, nm), key.trim(), path + nm));
            }
        }
    }

    private String readKeyFile(File f) {
        InputStream in = null;
        try {
            in = new FileInputStream(f);
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            byte[] buf = new byte[4096];
            int n;
            int total = 0;
            while ((n = in.read(buf)) > 0) {
                bo.write(buf, 0, n);
                total += n;
                if (total > 32768) break;
            }
            String text = new String(bo.toByteArray(), "UTF-8").trim();
            if (text.length() == 0) return null;
            if (text.indexOf("<string") >= 0 && text.indexOf("AuthKey") >= 0) {
                String k = extractFromPrefs(text);
                if (k != null && k.trim().length() > 0) return k.trim();
            }
            return text;
        } catch (Throwable t) {
            return null;
        } finally {
            try { if (in != null) in.close(); } catch (Throwable ignored) { }
        }
    }

    private String folderLabelOf(String path, String fileName) {
        String p = path;
        while (p.endsWith("/")) p = p.substring(0, p.length() - 1);
        if (p.length() > 0) {
            int i = p.lastIndexOf('/');
            String seg = i < 0 ? p : p.substring(i + 1);
            if (seg.length() > 0) return seg;
        }
        int dot = fileName.lastIndexOf('.');
        String base = dot > 0 ? fileName.substring(0, dot) : fileName;
        if ("authkey".equalsIgnoreCase(base)) return "导入的 key";
        return base;
    }

    private String readKeyDoc(android.net.Uri doc) {
        InputStream in = null;
        try {
            in = getContentResolver().openInputStream(doc);
            if (in == null) return null;
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            byte[] buf = new byte[4096];
            int n;
            int total = 0;
            while ((n = in.read(buf)) > 0) {
                bo.write(buf, 0, n);
                total += n;
                if (total > 32768) break;
            }
            String text = new String(bo.toByteArray(), "UTF-8").trim();
            if (text.length() == 0) return null;
            if (text.indexOf("<string") >= 0 && text.indexOf("AuthKey") >= 0) {
                String k = extractFromPrefs(text);
                if (k != null && k.trim().length() > 0) return k.trim();
            }
            return text;
        } catch (Throwable t) {
            return null;
        } finally {
            try { if (in != null) in.close(); } catch (Throwable ignored) { }
        }
    }

    private static boolean isKeyLike(String k) {
        if (k == null) return false;
        String t = k.trim();
        if (t.length() < 16 || t.length() > 512) return false;
        for (int i = 0; i < t.length(); i++) {
            char c = t.charAt(i);
            boolean ok = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')
                    || c == '-' || c == '_' || c == '.' || c == '=' || c == '+' || c == '/' || c == ':';
            if (!ok) return false;
        }
        return true;
    }

    private boolean libraryHasKey(String key) {
        if (key == null) return false;
        String k = key.trim();
        for (int i = 0; i < accounts.size(); i++) {
            if (accounts.get(i).key.trim().equals(k)) return true;
        }
        return false;
    }

    private String uniqueAccountName(String base) {
        String nm = (base == null || base.trim().length() == 0) ? "导入的 key" : base.trim();
        if (nm.length() > 30) nm = nm.substring(0, 30);
        boolean clash = true;
        String cand = nm;
        int n = 2;
        while (clash && n < 200) {
            clash = false;
            for (int i = 0; i < accounts.size(); i++) {
                if (accounts.get(i).name.equalsIgnoreCase(cand)) {
                    clash = true;
                    break;
                }
            }
            if (clash) cand = nm + " " + n;
            n++;
        }
        return cand;
    }

    private void showImportFolderResult(final android.net.Uri tree, final String rootLabel,
                                        final java.util.List<FoundKey> found) {
        final java.util.List<FoundKey> fresh = new java.util.ArrayList<FoundKey>();
        int dup = 0;
        for (int i = 0; i < found.size(); i++) {
            if (libraryHasKey(found.get(i).key)) dup++;
            else fresh.add(found.get(i));
        }
        LinearLayout c = dlgCard();
        if (fresh.isEmpty()) {
            dlgTitle(c, found.isEmpty() ? "没找到 key" : "都是账号库里已有的");
            String msg = found.isEmpty()
                    ? "在「" + rootLabel + "/」和它的子文件夹里没找到像 AuthKey 的文件。\n\n提示：导出的目录结构是 东放Key/账号名/AuthKey.txt，选「东放Key」或它的上一层就行；文件内容也得是一串不含空格的 key。"
                    : "找到 " + found.size() + " 个，但它们对应的 key 都已经在账号库里了，不用重复添加。";
            dlgSub(c, msg);
            final AlertDialog[] h = new AlertDialog[1];
            c.addView(dlgPrimary("知道了", new View.OnClickListener() {
                public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
            }));
            h[0] = showCard(c);
            return;
        }
        dlgTitle(c, "找到 " + found.size() + " 个 key");
        String head = "来自「" + rootLabel + "/」。确认后会加进「账号」分段";
        if (dup > 0) head += "，其中 " + dup + " 个已在账号库里，会自动跳过";
        dlgSub(c, head + "。");
        StringBuilder sb = new StringBuilder();
        int show = Math.min(fresh.size(), 8);
        for (int i = 0; i < show; i++) {
            FoundKey f = fresh.get(i);
            sb.append(i + 1).append(". ").append(f.name)
                    .append("  ·  ").append(hash(f.key).substring(0, 16))
                    .append("  ·  ").append(f.key.trim().length()).append("B\n");
        }
        if (fresh.size() > show) sb.append("… 还有 ").append(fresh.size() - show).append(" 个");
        TextView listTv = new TextView(this);
        listTv.setText(sb.toString());
        listTv.setTextSize(12.5f);
        listTv.setTextColor(c("#4B5563"));
        listTv.setLineSpacing(dp(4), 1f);
        listTv.setTypeface(android.graphics.Typeface.MONOSPACE);
        listTv.setPadding(0, dp(6), 0, dp(2));
        c.addView(listTv);
        final AlertDialog[] h = new AlertDialog[1];
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
        h[0] = showCard(c);
    }

    private void importFoundKeys(final java.util.List<FoundKey> list) {
        int n = 0;
        for (int i = 0; i < list.size(); i++) {
            FoundKey f = list.get(i);
            Account a = new Account(uniqueAccountName(f.name), f.key.trim());
            a.game = game.id;
            a.note = "从文件夹导入：" + f.path;
            accounts.add(a);
            n++;
            log("[导入] " + a.name + " (" + a.fp() + ") ← " + f.path);
        }
        saveVault();
        accTab = 0;
        refreshList();
        refreshAccountsView();
        toast("已导入 " + n + " 个账号");
        log("[导入] 完成，共 " + n + " 个账号进了账号库");

        LinearLayout c = dlgCard();
        dlgTitle(c, "导入完成");
        dlgSub(c, n + " 个 key 已经加进「账号」分段（只是账号库，游戏里登录的还是原来那个）。要切换登录，去账号页选中一个，点底部「导入到游戏」。");
        final AlertDialog[] h = new AlertDialog[1];
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
        h[0] = showCard(c);
    }

    // ---------- 局域网传输（手机开一个小网页，电脑浏览器直接下载） ----------

    private void showLanTransfer() {
        final LanServer srv;
        try {
            srv = new LanServer();
            srv.start();
        } catch (Throwable t) {
            toast("启动失败：" + t);
            return;
        }
        String ip = lanIp();
        if (ip == null) {
            toast("没连上 WiFi");
            srv.halt();
            return;
        }
        final String url = "http://" + ip + ":" + srv.port + "/?k=" + srv.code;
        LinearLayout c = dlgCard();
        dlgTitle(c, "局域网传输");
        dlgSub(c, "让手机和电脑连同一个 WiFi，在电脑浏览器里打开下面这个地址，就能看到账号列表并下载 key。\n\n关掉这个窗口就停止，不会一直开着。");
        TextView u = new TextView(this);
        u.setText(url);
        u.setTextSize(13);
        u.setTextColor(c("#2F6BFF"));
        u.setTypeface(android.graphics.Typeface.MONOSPACE);
        u.setTextIsSelectable(true);
        u.setPadding(dp(12), dp(12), dp(12), dp(12));
        u.setBackground(roundRect(c("#F2F4F8"), 10, 0, 0));
        c.addView(u);
        TextView tip = new TextView(this);
        tip.setText("配对码 " + srv.code + " 已经写进地址里；别人就算扫到 IP，没有这个码也打不开。");
        tip.setTextSize(11);
        tip.setTextColor(c("#9AA3B0"));
        tip.setPadding(dp(2), dp(8), dp(2), 0);
        c.addView(tip);
        final AlertDialog[] h = new AlertDialog[1];
        c.addView(dlgPrimary("复制地址", new View.OnClickListener() {
            public void onClick(View v) {
                try {
                    android.content.ClipboardManager cm = (android.content.ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
                    cm.setPrimaryClip(android.content.ClipData.newPlainText("lan", url));
                    toast("地址已复制");
                } catch (Throwable t) { toast("复制失败"); }
            }
        }));
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "停止", new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
        }, false);
        c.addView(row);
        h[0] = showCard(c);
        h[0].setOnDismissListener(new android.content.DialogInterface.OnDismissListener() {
            public void onDismiss(android.content.DialogInterface d) {
                srv.halt();
                log("[局域网] 已停止");
            }
        });
        log("[局域网] 已启动 " + url);
    }

    /** 取本机 WiFi/热点的 IPv4 地址。 */
    private String lanIp() {
        try {
            java.util.Enumeration<java.net.NetworkInterface> en = java.net.NetworkInterface.getNetworkInterfaces();
            while (en.hasMoreElements()) {
                java.net.NetworkInterface ni = en.nextElement();
                if (!ni.isUp() || ni.isLoopback()) continue;
                java.util.Enumeration<java.net.InetAddress> as = ni.getInetAddresses();
                while (as.hasMoreElements()) {
                    java.net.InetAddress a = as.nextElement();
                    if (a instanceof java.net.Inet4Address && !a.isLoopbackAddress()) {
                        String ip = a.getHostAddress();
                        if (ip != null && ip.startsWith("192.168.") || ip != null && ip.startsWith("10.")
                                || ip != null && ip.startsWith("172.")) return ip;
                    }
                }
            }
        } catch (Throwable ignored) {
        }
        return null;
    }

    /** 极简 HTTP 服务：只服务一个列表页 + 每个 key 的下载。 */
    private class LanServer extends Thread {
        final java.net.ServerSocket ss;
        final int port;
        final String code;
        volatile boolean running = true;

        LanServer() throws Exception {
            java.net.ServerSocket s = null;
            int p = 8765;
            for (int i = 0; i < 20; i++) {
                try {
                    s = new java.net.ServerSocket(p + i, 8, java.net.InetAddress.getByName("0.0.0.0"));
                    p = p + i;
                    break;
                } catch (Throwable ignored) {
                }
            }
            if (s == null) throw new Exception("没有可用端口");
            ss = s;
            port = p;
            code = String.format(Locale.US, "%04d", 1000 + new java.util.Random().nextInt(9000));
            setDaemon(true);
        }

        public void halt() {
            running = false;
            try { ss.close(); } catch (Throwable ignored) {}
        }

        public void run() {
            while (running) {
                java.net.Socket sk = null;
                try {
                    sk = ss.accept();
                    handle(sk);
                } catch (Throwable ignored) {
                } finally {
                    try { if (sk != null) sk.close(); } catch (Throwable ignored) {}
                }
            }
        }

        private void handle(java.net.Socket sk) {
            try {
                sk.setSoTimeout(8000);
                java.io.BufferedReader in = new java.io.BufferedReader(
                        new java.io.InputStreamReader(sk.getInputStream(), "UTF-8"));
                String line = in.readLine();
                if (line == null) return;
                String[] parts = line.split(" ");
                if (parts.length < 2) return;
                String path = parts[1];
                java.io.OutputStream out = sk.getOutputStream();
                if (path.startsWith("/?k=" + code) || path.equals("/?k=" + code)) {
                    byte[] body = lanPage().getBytes("UTF-8");
                    head(out, "200 OK", "text/html; charset=utf-8", body.length);
                    out.write(body);
                } else if (path.startsWith("/key?i=") && path.contains("k=" + code)) {
                    int i = Integer.parseInt(path.substring(7, path.indexOf('&')));
                    java.util.List<Account> list = lanList();
                    if (i < 0 || i >= list.size()) {
                        head(out, "404 Not Found", "text/plain; charset=utf-8", 0);
                    } else {
                        Account a = list.get(i);
                        byte[] body = a.key.getBytes("UTF-8");
                        head(out, "200 OK", "application/octet-stream", body.length,
                                "attachment; filename=\"AuthKey.txt\"");
                        out.write(body);
                    }
                } else {
                    byte[] body = "配对码不对。请在 App 里重新打开局域网传输，用完整的地址。".getBytes("UTF-8");
                    head(out, "403 Forbidden", "text/plain; charset=utf-8", body.length);
                    out.write(body);
                }
                out.flush();
            } catch (Throwable ignored) {
            }
        }

        private void head(java.io.OutputStream out, String status, String type, int len) throws Exception {
            head(out, status, type, len, null);
        }

        private void head(java.io.OutputStream out, String status, String type, int len, String disp) throws Exception {
            StringBuilder h = new StringBuilder();
            h.append("HTTP/1.1 ").append(status).append("\r\n");
            h.append("Content-Type: ").append(type).append("\r\n");
            h.append("Content-Length: ").append(len).append("\r\n");
            h.append("Connection: close\r\n");
            if (disp != null) h.append("Content-Disposition: ").append(disp).append("\r\n");
            h.append("\r\n");
            out.write(h.toString().getBytes("UTF-8"));
        }

        private java.util.List<Account> lanList() {
            java.util.List<Account> l = new ArrayList<Account>();
            for (Account a : accounts) if (inGame(a) && !a.isBackup()) l.add(a);
            return l;
        }

        private String lanPage() {
            java.util.List<Account> l = lanList();
            StringBuilder b = new StringBuilder();
            b.append("<!doctype html><html><head><meta charset=\"utf-8\">");
            b.append("<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">");
            b.append("<title>东放 Key 管家 · 局域网传输</title><style>");
            b.append("body{font:15px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',sans-serif;");
            b.append("background:#f2f3f6;color:#101418;margin:0;padding:24px}");
            b.append(".w{max-width:640px;margin:0 auto}h1{font-size:20px;margin:0 0 4px}");
            b.append(".s{color:#8a93a0;font-size:13px;margin-bottom:18px}");
            b.append(".i{background:#fff;border:1px solid #e7ebf2;border-radius:14px;padding:14px 16px;margin-bottom:10px}");
            b.append(".n{font-weight:600}.m{color:#8a93a0;font-size:12px;margin-top:2px}");
            b.append("a{display:inline-block;margin-top:8px;background:#2f6bff;color:#fff;text-decoration:none;");
            b.append("padding:7px 14px;border-radius:9px;font-size:13px}");
            b.append(".f{color:#9aa3b0;font-size:12px;margin-top:18px}");
            b.append("</style></head><body><div class=\"w\">");
            b.append("<h1>").append(esc(game.label)).append(" · Key 列表</h1>");
            b.append("<div class=\"s\">共 ").append(l.size()).append(" 个账号 · 只在这台手机上开着这个窗口时能访问</div>");
            for (int i = 0; i < l.size(); i++) {
                Account a = l.get(i);
                b.append("<div class=\"i\"><div class=\"n\">").append(esc(a.name)).append("</div>");
                b.append("<div class=\"m\">指纹 ").append(a.fpShort()).append(" · ").append(a.key.length()).append("B");
                if (a.note != null && a.note.length() > 0) b.append(" · ").append(esc(a.note));
                b.append("</div><a href=\"/key?i=").append(i).append("&k=").append(code).append("\">下载 AuthKey.txt</a></div>");
            }
            b.append("<div class=\"f\">下载下来的是原始的 key 文本，放进游戏对应的 AuthKey 路径即可。关掉 App 里的窗口后这个页面就打不开了。</div>");
            b.append("</div></body></html>");
            return b.toString();
        }

        private String esc(String s) {
            if (s == null) return "";
            return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;");
        }
    }

    // ---------- 二维码 ----------

    /** 扫一扫：直接调系统相机拍照，拍完回来识别二维码。 */
    private void pickQrShot() {
        try {
            File dir = new File(getCacheDir(), "qr");
            if (!dir.exists()) dir.mkdirs();
            File f = new File(dir, "shot-" + System.currentTimeMillis() + ".jpg");
            pendingShot = f;
            Intent i = new Intent(android.provider.MediaStore.ACTION_IMAGE_CAPTURE);
            i.putExtra(android.provider.MediaStore.EXTRA_OUTPUT, ApkProvider.uriForShot(f));
            i.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION | Intent.FLAG_GRANT_READ_URI_PERMISSION);
            startActivityForResult(i, REQ_QR_SHOT);
        } catch (Throwable t) {
            log("[二维码] 相机打不开：" + t);
            toast("相机打不开，改成从相册选图");
            pendingShot = null;
            pickQrImage();
        }
    }

    private void pickQrImage() {
        try {
            Intent i = new Intent(Intent.ACTION_GET_CONTENT);
            i.setType("image/*");
            i.addCategory(Intent.CATEGORY_OPENABLE);
            startActivityForResult(Intent.createChooser(i, "选一张二维码图片"), REQ_QR_IMG);
        } catch (Throwable t) {
            toast("打不开图片选择器");
        }
    }

    private void decodeQrUri(final android.net.Uri uri) {
        log("[二维码] 正在识别图片…");
        pool.execute(new Runnable() {
            public void run() {
                String text = null;
                String err = null;
                try {
                    android.graphics.BitmapFactory.Options o = new android.graphics.BitmapFactory.Options();
                    o.inJustDecodeBounds = true;
                    android.graphics.BitmapFactory.decodeStream(getContentResolver().openInputStream(uri), null, o);
                    int scale = 1;
                    while (o.outWidth / scale > 1400 || o.outHeight / scale > 1400) scale *= 2;
                    android.graphics.BitmapFactory.Options o2 = new android.graphics.BitmapFactory.Options();
                    o2.inSampleSize = scale;
                    android.graphics.Bitmap bm = android.graphics.BitmapFactory.decodeStream(
                            getContentResolver().openInputStream(uri), null, o2);
                    if (bm == null) throw new Exception("图片读不出来");
                    int w = bm.getWidth(), h = bm.getHeight();
                    int[] px = new int[w * h];
                    bm.getPixels(px, 0, w, 0, 0, w, h);
                    com.google.zxing.RGBLuminanceSource src = new com.google.zxing.RGBLuminanceSource(w, h, px);
                    com.google.zxing.BinaryBitmap bb = new com.google.zxing.BinaryBitmap(
                            new com.google.zxing.common.HybridBinarizer(src));
                    com.google.zxing.Result rr = new com.google.zxing.MultiFormatReader().decode(bb);
                    text = rr.getText();
                } catch (com.google.zxing.NotFoundException nf) {
                    err = "图片里没有二维码，或者二维码太糊";
                } catch (Throwable t) {
                    err = "识别失败：" + t;
                }
                final String tt = text;
                final String ee = err;
                runOnUiThread(new Runnable() {
                    public void run() {
                        if (tt == null) {
                            log("[二维码] " + ee);
                            toast(ee == null ? "没识别出内容" : ee);
                            return;
                        }
                        String k = tt.trim();
                        if (k.contains("<string") && k.contains("AuthKey")) {
                            String x = extractFromPrefs(k);
                            if (x != null && x.trim().length() > 0) k = x.trim();
                        }
                        if (!isKeyLike(k)) {
                            log("[二维码] 解出来的内容不像 key（" + k.length() + " 字符）");
                            toast("二维码里不是 key");
                            return;
                        }
                        log("[二维码] 已识别出 key，指纹 " + hash(k).substring(0, 16));
                        if (libraryHasKey(k)) toast("这个 key 账号库里已经有了");
                        askNameThenSave(k, "二维码");
                    }
                });
            }
        });
    }

    private void makeQr(final Account a) {
        pool.execute(new Runnable() {
            public void run() {
                File out = null;
                try {
                    int S = 660;
                    java.util.Hashtable<com.google.zxing.EncodeHintType, Object> hints =
                            new java.util.Hashtable<com.google.zxing.EncodeHintType, Object>();
                    hints.put(com.google.zxing.EncodeHintType.CHARACTER_SET, "UTF-8");
                    hints.put(com.google.zxing.EncodeHintType.MARGIN, 2);
                    com.google.zxing.common.BitMatrix m = new com.google.zxing.qrcode.QRCodeWriter()
                            .encode(a.key, com.google.zxing.BarcodeFormat.QR_CODE, S, S, hints);
                    int[] px = new int[S * S];
                    for (int y = 0; y < S; y++) {
                        for (int x = 0; x < S; x++) {
                            px[y * S + x] = m.get(x, y) ? 0xFF101418 : 0xFFFFFFFF;
                        }
                    }
                    android.graphics.Bitmap bm = android.graphics.Bitmap.createBitmap(S, S, android.graphics.Bitmap.Config.ARGB_8888);
                    bm.setPixels(px, 0, S, 0, 0, S, S);
                    File dir = new File(getCacheDir(), "qr");
                    if (!dir.exists()) dir.mkdirs();
                    out = new File(dir, safeName(a.name) + "-" + a.fpShort() + ".png");
                    java.io.FileOutputStream fo = new java.io.FileOutputStream(out);
                    bm.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, fo);
                    fo.close();
                } catch (Throwable t) {
                    log("[二维码] 生成失败：" + t);
                    out = null;
                }
                final File f = out;
                runOnUiThread(new Runnable() {
                    public void run() {
                        if (f == null) { toast("生成二维码失败"); return; }
                        log("[二维码] 已生成 " + f.getName());
                        LinearLayout c = dlgCard();
                        dlgTitle(c, a.name);
                        dlgSub(c, "扫这个二维码就能拿到 key。发给别人等于把账号交给对方，注意场合。");
                        android.widget.ImageView iv = new android.widget.ImageView(MainActivity.this);
                        android.graphics.Bitmap bm2 = android.graphics.BitmapFactory.decodeFile(f.getAbsolutePath());
                        iv.setImageBitmap(bm2);
                        iv.setAdjustViewBounds(true);
                        iv.setBackground(roundRect(c("#FFFFFF"), 12, 0, 0));
                        iv.setPadding(dp(8), dp(8), dp(8), dp(8));
                        LinearLayout.LayoutParams ilp = new LinearLayout.LayoutParams(
                                ViewGroup.LayoutParams.MATCH_PARENT, dp(230));
                        ilp.setMargins(0, dp(8), 0, 0);
                        c.addView(iv, ilp);
                        final AlertDialog[] h = new AlertDialog[1];
                        c.addView(dlgPrimary("分享这张二维码", new View.OnClickListener() {
                            public void onClick(View v) {
                                if (h[0] != null) h[0].dismiss();
                                try {
                                    android.net.Uri u = ApkProvider.uriForQr(f);
                                    Intent sh = new Intent(Intent.ACTION_SEND);
                                    sh.setType("image/png");
                                    sh.putExtra(Intent.EXTRA_STREAM, u);
                                    sh.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                                    startActivity(Intent.createChooser(sh, "分享二维码"));
                                } catch (Throwable t) {
                                    toast("分享失败：" + t);
                                }
                            }
                        }));
                        LinearLayout row = dlgBtnRow();
                        dlgAddGhost(row, "关闭", new View.OnClickListener() {
                            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
                        }, false);
                        c.addView(row);
                        h[0] = showCard(c);
                    }
                });
            }
        });
    }

    // ---------- 导入历史 / 备份保留 / 撤销 / 打包导出 ----------

    private String backupKeep() {
        return getPreferences(MODE_PRIVATE).getString("backupKeep", "all");
    }

    private String keepLabel(String k) {
        if ("10".equals(k)) return "最近 10 份";
        if ("30d".equals(k)) return "最近 30 天";
        return "永久保留";
    }

    private void chooseBackupKeep() {
        final String[] keys = new String[]{"all", "10", "30d"};
        String[] labels = new String[]{"永久保留（默认）", "最近 10 份", "最近 30 天"};
        LinearLayout c = dlgCard();
        dlgTitle(c, "自动备份保留");
        dlgSub(c, "超出的自动备份会从账号库移除，导出的文件夹也会一起删。当前：" + keepLabel(backupKeep()) + "。");
        final AlertDialog[] h = new AlertDialog[1];
        for (int i = 0; i < keys.length; i++) {
            final String k = keys[i];
            boolean on = k.equals(backupKeep());
            c.addView(dlgMenuItem(labels[i] + (on ? "  ✓" : ""), on ? "当前选择" : "", false, new View.OnClickListener() {
                public void onClick(View v) {
                    getPreferences(MODE_PRIVATE).edit().putString("backupKeep", k).apply();
                    if (rowKeepVal != null) rowKeepVal.setText(keepLabel(k));
                    if (h[0] != null) h[0].dismiss();
                    pruneBackups();
                    refreshList();
                    toast("已改为「" + keepLabel(k) + "」");
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

    /** 按保留策略清掉多余的自动备份（只动 backup，不动账号）。 */
    private void pruneBackups() {
        String keep = backupKeep();
        if ("all".equals(keep)) return;
        java.util.List<Account> bs = new ArrayList<Account>();
        for (Account a : accounts) if (a.isBackup() && inGame(a)) bs.add(a);
        if (bs.size() == 0) return;
        java.util.Collections.sort(bs, new java.util.Comparator<Account>() {
            public int compare(Account x, Account y) {
                String cx = x.created == null ? "" : x.created;
                String cy = y.created == null ? "" : y.created;
                return cy.compareTo(cx); // 新的在前
            }
        });
        long cutoff = 0L;
        if ("30d".equals(keep)) cutoff = System.currentTimeMillis() - 30L * 24 * 3600 * 1000;
        java.util.List<Account> kill = new ArrayList<Account>();
        for (int i = 0; i < bs.size(); i++) {
            Account a = bs.get(i);
            boolean drop = false;
            if ("10".equals(keep)) drop = i >= 10;
            if (cutoff > 0) {
                long t = 0L;
                try {
                    t = new java.text.SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US).parse(a.created == null ? "" : a.created).getTime();
                } catch (Throwable ignored) {
                }
                if (t > 0 && t < cutoff) drop = true;
            }
            if (drop) kill.add(a);
        }
        if (kill.size() == 0) return;
        for (Account a : kill) {
            if (a.folder != null && a.folder.length() > 0) {
                try {
                    File f = exportFileOf(a);
                    if (f != null && f.exists()) f.delete();
                } catch (Throwable ignored) {
                }
            }
            accounts.remove(a);
        }
        saveVault();
        log("[备份] 按「" + keepLabel(keep) + "」清掉了 " + kill.size() + " 份旧备份");
    }

    private void recordImportHistory(String toName, String prevKey, String targetKey, String backupName) {
        try {
            SharedPreferences sp = getPreferences(MODE_PRIVATE);
            String raw = sp.getString("importHistory", "[]");
            JSONArray arr = new JSONArray(raw);
            JSONObject o = new JSONObject();
            o.put("t", stamp());
            o.put("to", toName);
            o.put("prevFp", hash(prevKey).substring(0, 16));
            o.put("toFp", hash(targetKey == null ? "" : targetKey).substring(0, 16));
            o.put("backup", backupName == null ? "" : backupName);
            JSONArray out = new JSONArray();
            out.put(o);
            for (int i = 0; i < arr.length() && out.length() < 100; i++) out.put(arr.get(i));
            sp.edit().putString("importHistory", out.toString()).apply();
        } catch (Throwable t) {
            log("[历史] 记录失败：" + t);
        }
    }

    private void showImportHistory() {
        LinearLayout c = dlgCard();
        dlgTitle(c, "导入历史");
        final AlertDialog[] h = new AlertDialog[1];
        try {
            JSONArray arr = new JSONArray(getPreferences(MODE_PRIVATE).getString("importHistory", "[]"));
            if (arr.length() == 0) {
                dlgSub(c, "还没有导入记录。每次把 key 写进游戏后，这里会记下时间、换成了谁、原来的 key 备份在哪。");
            } else {
                dlgSub(c, "最近 " + Math.min(arr.length(), 12) + " 次。点一条可以把游戏回到那一次之前的 key。");
                int n = Math.min(arr.length(), 12);
                for (int i = 0; i < n; i++) {
                    final JSONObject o = arr.getJSONObject(i);
                    final String bak = o.optString("backup", "");
                    String t = o.optString("t", "");
                    String to = o.optString("to", "");
                    String prevFp = o.optString("prevFp", "");
                    c.addView(dlgMenuItem(t + "  →  " + to,
                            "换成这之前：指纹 " + prevFp + (bak.length() == 0 ? " · 没有可用的备份" : " · 备份「" + bak + "」"),
                            false, new View.OnClickListener() {
                                public void onClick(View v) {
                                    if (h[0] != null) h[0].dismiss();
                                    rollbackTo(bak);
                                }
                            }));
                }
            }
        } catch (Throwable t) {
            dlgSub(c, "读历史失败：" + t);
        }
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "关闭", new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
        }, true);
        c.addView(row);
        h[0] = showCard(c);
    }

    private void rollbackTo(String backupName) {
        if (backupName == null || backupName.length() == 0) {
            toast("这条记录没有可用的备份");
            return;
        }
        Account bak = null;
        for (Account a : accounts) if (a.isBackup() && backupName.equals(a.name)) { bak = a; break; }
        if (bak == null) {
            toast("备份「" + backupName + "」已经不在账号库里了");
            return;
        }
        log("[历史] 回滚到「" + backupName + "」");
        doImportNow(bak);
    }

    /** 撤销刚做的导入：把上一次的 key 写回游戏。 */
    private void undoImport(final String prevKey, final String targetName) {
        LinearLayout c = dlgCard();
        dlgTitle(c, "撤销这次导入？");
        dlgSub(c, "会把游戏里的 key 写回导入「" + targetName + "」之前的那个，并校验。不会删掉账号库里的「" + targetName + "」。");
        final AlertDialog[] h = new AlertDialog[1];
        c.addView(dlgPrimary("撤销", new View.OnClickListener() {
            public void onClick(View v) {
                if (h[0] != null) h[0].dismiss();
                if (!permReady()) { showNoPerm(); return; }
                log("--- 撤销导入，写回原 key ---");
                pool.execute(new Runnable() {
                    public void run() {
                        shell("am force-stop " + PKG, 15000);
                        boolean ok = writeKey(prevKey.getBytes());
                        byte[] back = readKeyAt(EXT_KEY);
                        String got = back == null ? "" : new String(back).trim();
                        boolean same = got.equals(prevKey.trim());
                        log(ok && same ? "[撤销] 已写回原 key 并校验通过" : "[撤销] 写回失败，请用备份文件手动恢复");
                        curFpLoaded = false;
                        runOnUiThread(new Runnable() {
                            public void run() {
                                refreshCurrentFp();
                                toast(ok && same ? "已撤销，游戏回到上一个 key" : "撤销失败，请手动恢复");
                            }
                        });
                    }
                });
            }
        }));
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "取消", new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
        }, false);
        c.addView(row);
        h[0] = showCard(c);
    }

    /** 任务页：把账号库里的 key 打包成一个 zip。 */
    private void startZipExport() {
        if (countAccounts() == 0) {
            toast("账号库里还没有账号");
            return;
        }
        try {
            Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);
            i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                    | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);
            startActivityForResult(i, REQ_TREE_ZIP);
        } catch (Throwable t) {
            toast("打不开文件夹选择器");
        }
    }

    private void writeZipToTree(final Uri tree) {
        final String label = treeLabel(tree);
        log("[打包] 目标文件夹 " + label);
        pool.execute(new Runnable() {
            public void run() {
                String name = "东放Key-" + game.label + "-"
                        + new java.text.SimpleDateFormat("yyyyMMdd-HHmm", Locale.US).format(new java.util.Date()) + ".zip";
                int n = 0;
                try {
                    String docId = android.provider.DocumentsContract.getTreeDocumentId(tree);
                    Uri parent = android.provider.DocumentsContract.buildDocumentUriUsingTree(tree, docId);
                    Uri out = android.provider.DocumentsContract.createDocument(getContentResolver(), parent, "application/zip", name);
                    java.util.zip.ZipOutputStream zos = new java.util.zip.ZipOutputStream(
                            new java.io.BufferedOutputStream(getContentResolver().openOutputStream(out)));
                    StringBuilder man = new StringBuilder();
                    man.append("Housamo AuthKey Manager\n");
                    man.append("游戏: ").append(game.label).append("\n");
                    man.append("时间: ").append(stamp()).append("\n");
                    man.append("说明: 每个子文件夹里的 AuthKey.txt 就是一个账号的 key。\n\n");
                    man.append("文件夹\t指纹\t大小\t创建时间\t备注\n");
                    for (Account a : accounts) {
                        if (!inGame(a) || a.isBackup()) continue;
                        String dir = safeName(a.name);
                        zos.putNextEntry(new java.util.zip.ZipEntry(dir + "/AuthKey.txt"));
                        zos.write(a.key.getBytes("UTF-8"));
                        zos.closeEntry();
                        man.append(dir).append("\t").append(a.fpShort()).append("\t")
                                .append(a.key.length()).append("B\t").append(a.created).append("\t")
                                .append(a.note == null ? "" : a.note).append("\n");
                        n++;
                    }
                    zos.putNextEntry(new java.util.zip.ZipEntry("manifest.txt"));
                    zos.write(man.toString().getBytes("UTF-8"));
                    zos.closeEntry();
                    zos.finish();
                    zos.close();
                } catch (Throwable t) {
                    log("[打包] 失败：" + t);
                    toast("打包失败：" + t);
                    return;
                }
                final int count = n;
                log("[打包] 已写入 " + count + " 个 key → " + label + "/" + name);
                runOnUiThread(new Runnable() {
                    public void run() {
                        LinearLayout c = dlgCard();
                        dlgTitle(c, "打包完成");
                        dlgSub(c, "已把 " + count + " 个账号写进 " + label + "/" + name + "，里面还有一个 manifest.txt 写着每个账号的指纹。");
                        final AlertDialog[] h = new AlertDialog[1];
                        c.addView(dlgPrimary("知道了", new View.OnClickListener() {
                            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
                        }));
                        h[0] = showCard(c);
                    }
                });
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
                            "https://api.github.com/repos/fenghuo6183/HousamoAuthKeyManager/releases?per_page=20").openConnection();
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
                    // 按 release 逐段找：取「第一个带 .apk 资产的版本」，避免把只发 Windows 包的版本当成新版 App
                    java.util.regex.Matcher m1 = java.util.regex.Pattern.compile("\"tag_name\"\\s*:\\s*\"([^\"]+)\"").matcher(body);
                    java.util.List<Integer> tags = new ArrayList<Integer>();
                    java.util.List<String> names = new ArrayList<String>();
                    while (m1.find()) {
                        tags.add(m1.start());
                        names.add(m1.group(1));
                    }
                    for (int i = 0; i < tags.size(); i++) {
                        int from = tags.get(i);
                        int to = i + 1 < tags.size() ? tags.get(i + 1) : body.length();
                        String seg = body.substring(from, to);
                        java.util.regex.Matcher ma = java.util.regex.Pattern.compile("\"browser_download_url\"\\s*:\\s*\"([^\"]+\\.apk)\"").matcher(seg);
                        if (!ma.find()) continue;
                        tag = names.get(i);
                        apk = ma.group(1);
                        java.util.regex.Matcher mu = java.util.regex.Pattern.compile("\"html_url\"\\s*:\\s*\"([^\"]+)\"").matcher(seg);
                        if (mu.find()) url = mu.group(1);
                        break;
                    }
                    if (tag == null && !names.isEmpty()) {
                        tag = names.get(0);
                        String seg0 = body.substring(tags.get(0), tags.size() > 1 ? tags.get(1) : body.length());
                        java.util.regex.Matcher mu = java.util.regex.Pattern.compile("\"html_url\"\\s*:\\s*\"([^\"]+)\"").matcher(seg0);
                        if (mu.find()) url = mu.group(1);
                    }
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
                        log("[更新] 本地 " + CURRENT_VER + " / 远端 " + (ver.length() == 0 ? "读取失败" : ver) + (apkUrl == null ? "（无 APK 资产）" : ""));
                        if (rowUpdateVal != null) {
                            rowUpdateVal.setText(cmp > 0 ? "发现 " + ver + "，点此更新" : "已是最新版 " + CURRENT_VER);
                            rowUpdateVal.setTextColor(cmp > 0 ? c("#2F6BFF") : c("#9AA3B0"));
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
        if (lockOn() && !unlocked) {
            if (lastBgAt == 0L || System.currentTimeMillis() - lastBgAt > 30000L) {
                host.postDelayed(new Runnable() {
                    public void run() { if (!unlocked) showLockScreen(); }
                }, 120L);
            }
        }
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
        if (req == REQ_QR_SHOT) {
            File shot = pendingShot;
            pendingShot = null;
            if (shot == null) return;
            if (res == RESULT_OK && shot.length() > 0) {
                decodeQrUri(android.net.Uri.fromFile(shot));
            } else {
                shot.delete();
                toast("没拍到照片，重试一次或改用相册选图");
            }
            return;
        }
        if (res != RESULT_OK || data == null || data.getData() == null) return;
        android.net.Uri uri = data.getData();
        if (req == REQ_QR_IMG) {
            decodeQrUri(uri);
            return;
        }
        if (req != REQ_TREE && req != REQ_TREE_COPY && req != REQ_TREE_BAK && req != REQ_TREE_IMPORT && req != REQ_TREE_ZIP) return;
        try {
            getContentResolver().takePersistableUriPermission(uri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        } catch (Throwable ignored) {
        }
        if (req == REQ_TREE_IMPORT) {
            scanFolderForKeys(uri);
            return;
        }
        if (req == REQ_TREE_ZIP) {
            writeZipToTree(uri);
            return;
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
        t.setTextColor(c(fg));
        t.setBackground(roundRect(c(bg), 20, 0, 0));
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
        LinearLayout c = dlgCard();
        dlgTitle(c, a.isBackup() ? a.name.replace("导入前备份", "备份") : a.name);
        dlgSub(c, "指纹 " + a.fpShort() + (a.isBackup() ? " · 自动备份" : " · 账号"));
        final AlertDialog[] h = new AlertDialog[1];
        c.addView(dlgMenuItem("导入到游戏", "写进游戏，覆盖当前登录的 key", false, new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); doImport(); }
        }));
        c.addView(dlgMenuItem("改备注", "给自己看的说明，比如「日服小号」", false, new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); doEditNote(); }
        }));
        c.addView(dlgMenuItem("生成二维码", "把这个 key 做成二维码图片，方便当面发给另一台手机", false, new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); makeQr(a); }
        }));
        c.addView(dlgMenuItem("复制指纹", "复制 " + a.fpShort() + "，发给别人核对用", false, new View.OnClickListener() {
            public void onClick(View v) {
                if (h[0] != null) h[0].dismiss();
                try {
                    android.content.ClipboardManager cm = (android.content.ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
                    cm.setPrimaryClip(android.content.ClipData.newPlainText("fingerprint", a.fpShort()));
                    toast("指纹已复制：" + a.fpShort());
                } catch (Throwable t) { toast("复制失败"); }
            }
        }));
        if (!a.isBackup()) c.addView(dlgMenuItem("重命名", "只改账号库里显示的名字", false, new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); doRename(); }
        }));
        c.addView(dlgMenuItem("删除", a.isBackup() ? "只删这条备份，导出文件不动" : "从账号库移除，导出文件不动", true, new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); doDelete(); }
        }));
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "取消", new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
        }, true);
        c.addView(row);
        h[0] = showCard(c);
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
                        refreshHomeOverview();
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
        c.setBackground(roundRect(c("#FFF8E6"), 16, c("#F0D9A8"), 1));
        c.setPadding(dp(14), dp(12), dp(14), dp(12));
        TextView t = new TextView(this);
        t.setText("游戏里的 key 和账号库对不上");
        t.setTextSize(15);
        t.setTextColor(c("#8A6D1F"));
        t.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);
        c.addView(t);
        TextView d = new TextView(this);
        String msg = "「" + game.label + "」现在用的指纹是 " + curFp + "，账号库里没有这个 key。";
        if (latest != null) msg += "\n库里最新的是「" + latest.name + "」（" + latest.fpShort() + "）。";
        msg += "\n想留一份，就点「存到账号库」。";
        d.setText(msg);
        d.setTextSize(12);
        d.setTextColor(c("#7A6633"));
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
        t.setTextColor(c("#1B1F24"));
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
            h.setTextColor(c("#9AA3B0"));
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
        LinearLayout c = dlgCard();
        dlgTitle(c, "放到其他文件夹");
        dlgSub(c, "会打开系统的文件夹选择器，选一个目标目录，写进去之后可以随时再用文件管理器挪走。");
        final AlertDialog[] h = new AlertDialog[1];
        c.addView(dlgMenuItem("复制一份", "原来的导出文件保留，目标文件夹里多一份", false, new View.OnClickListener() {
            public void onClick(View v) {
                copyTarget = a;
                copyMove = false;
                if (h[0] != null) h[0].dismiss();
                startTreePick();
            }
        }));
        c.addView(dlgMenuItem("移动过去", "写成功后删掉原来导出的那一份", false, new View.OnClickListener() {
            public void onClick(View v) {
                copyTarget = a;
                copyMove = true;
                if (h[0] != null) h[0].dismiss();
                startTreePick();
            }
        }));
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "取消", new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
        }, true);
        c.addView(row);
        h[0] = showCard(c);
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
        LinearLayout c = dlgCard();
        dlgTitle(c, "重命名");
        dlgSub(c, "只改本机账号库里显示的名字，导出到 Download 的文件名不变。");
        final EditText et = dlgInput(a.name);
        et.selectAll();
        c.addView(et);
        final AlertDialog[] h = new AlertDialog[1];
        c.addView(dlgPrimary("保存", new View.OnClickListener() {
            public void onClick(View v) {
                String n = et.getText().toString().trim();
                if (n.length() > 0) {
                    a.name = n;
                    saveVault();
                    refreshList();
                    log("[改名] 已改名为 " + n);
                }
                if (h[0] != null) h[0].dismiss();
            }
        }));
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "取消", new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
        }, false);
        c.addView(row);
        h[0] = showCard(c);
    }

    private void doDelete() {
        final Account a = selected();
        if (a == null) {
            toast("请先选中一个账号");
            return;
        }
        LinearLayout c = dlgCard();
        dlgTitle(c, a.isBackup() ? "删除这条备份" : "删除账号");
        dlgSub(c, "确定删除「" + a.name + "」？" + (a.isBackup() ? "已导出的 AuthKey.txt 不会删。" : "这条记录会从本机账号库消失，导出过的文件仍在原处。"));
        final AlertDialog[] h = new AlertDialog[1];
        Button del = dlgPrimary("删除", new View.OnClickListener() {
            public void onClick(View v) {
                accounts.remove(a);
                saveVault();
                refreshList();
                log("[删除] 已删除 " + a.name);
                if (h[0] != null) h[0].dismiss();
            }
        });
        del.setBackground(roundRect(c("#E5484D"), 12, 0, 0));
        c.addView(del);
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "取消", new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
        }, false);
        c.addView(row);
        h[0] = showCard(c);
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
        java.util.List<File> roots = new ArrayList<File>();
        roots.add(exportRootGameDir());
        // 东放老版本把账号文件夹直接铺在 东放Key/ 根下，继续扫一遍，老用户已有的导出不会丢。
        if ("housamo".equals(game.id)) roots.add(exportRootFileDefault());
        for (File root : roots) scanRootDir(root, out);
        Uri tree = exportTreeForGame();
        if (tree != null) scanTreeChildren(out, tree, exportRootLabelFull());
        if ("housamo".equals(game.id)) {
            Uri legacy = exportRootUri();
            if (legacy != null && !legacy.equals(tree)) scanTreeChildren(out, legacy, exportRootLabel());
        }
        return out;
    }

    /** 目录名是不是某个游戏的专属文件夹（东京放课后 / LiveAHero）。 */
    private boolean isGameFolderName(String nm) {
        for (Game g : GAMES) if (g.label.equals(nm)) return true;
        return false;
    }

    /** 扫描一个根目录下「一个 key 一个子文件夹」的结构。 */
    private void scanRootDir(File root, List<Account> out) {
        try {
            File[] dirs = root.listFiles();
            if (dirs == null) return;
            for (File d : dirs) {
                if (d == null || !d.isDirectory()) continue;
                String nm = d.getName();
                if (nm.startsWith("_")) continue;
                if (nm.equals("导入前备份")) continue;
                if (isGameFolderName(nm)) continue;
                File f = new File(d, "AuthKey.txt");
                if (!f.isFile()) continue;
                String k = readTextFile(f);
                if (k == null) continue;
                k = k.trim();
                if (k.length() < 8) continue;
                Account a = new Account(safeName(nm), k);
                a.game = game.id;
                a.note = "来自导出文件夹";
                a.folder = f.getAbsolutePath();
                out.add(a);
            }
        } catch (Throwable t) {
            log("[账号] 读导出文件夹失败：" + t);
        }
    }

    /** 扫描 SAF 目录树下一层的「一个 key 一个子文件夹」结构。 */
    private void scanTreeChildren(List<Account> out, Uri tree, String label) {
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
                if (nm.equals("导入前备份") || isGameFolderName(nm)) continue;
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
                a.folder = label + nm + "/AuthKey.txt";
                out.add(a);
            }
        } catch (Throwable t) {
            log("[账号] 读自定义导出目录失败：" + t);
        } finally {
            try { if (c != null) c.close(); } catch (Throwable ignored) { }
        }
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

    /** 默认备份目录（带游戏子目录）的展示文案。 */
    private String backupDefaultLabel() {
        return exportRelPrefix() + "导入前备份/";
    }

    private String backupRootLabel() {
        String l = getPreferences(MODE_PRIVATE).getString("backupRootLabel", "");
        return l.length() == 0 ? backupDefaultLabel() : l;
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
                + "/东放Key/" + game.exportSub() + "/导入前备份";
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
        String rel = backupDefaultLabel() + name;
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
                cv.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/东放Key/" + game.exportSub() + "/导入前备份");
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
        body.setTextColor(c("#3A4250"));
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
        tip.setTextColor(c("#8A93A0"));
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
        LinearLayout c = dlgCard();
        dlgTitle(c, "导入到游戏？");
        dlgSub(c, msg);
        final AlertDialog[] h = new AlertDialog[1];
        c.addView(dlgPrimary("导入", new View.OnClickListener() {
            public void onClick(View v) {
                if (h[0] != null) h[0].dismiss();
                doImportNow(a);
            }
        }));
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "取消", new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
        }, false);
        c.addView(row);
        h[0] = showCard(c);
    }

    private void doImportNow(final Account a) {
        if (!permReady()) { showNoPerm(); return; }
        log("--- 开始导入：" + a.name + " ---");
        pool.execute(new Runnable() {
            public void run() {
                // 1. 备份现有 key
                final boolean[] backupOk = {true};
                String bakNameForHistory = null;
                String old = null;
                byte[] cur = readKeyAt(EXT_KEY);
                if (cur == null) cur = readKeyAt(PREFS1);
                if (cur != null) {
                    old = new String(cur).trim();
                    if (old.length() >= 8) {
                        Account already = findBackupOfKey(old);
                        if (already != null) {
                            log("[备份] 这个 key 已经备份过（" + already.name + "），跳过重复备份");
                            bakNameForHistory = already.name;
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
                        bakNameForHistory = bak.name;
                        runOnUiThread(new Runnable() {
                            public void run() {
                                accounts.add(bak);
                                saveVault();
                                pruneBackups();
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
                final String histBackup = bakNameForHistory;
                if (prevKey != null && prevKey.length() >= 8) recordImportHistory(a.name, prevKey, a.key, histBackup);
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
                        LinearLayout c = dlgCard();
                        dlgTitle(c, "导入完成");
                        dlgSub(c, "已写入并校验通过。点「打开游戏」，进去就是「" + a.name + "」这个账号。");
                        final AlertDialog[] h = new AlertDialog[1];
                        c.addView(dlgPrimary("打开游戏", new View.OnClickListener() {
                            public void onClick(View v) {
                                if (h[0] != null) h[0].dismiss();
                                launchGame();
                            }
                        }));
                        LinearLayout row = dlgBtnRow();
                        if (prevKey != null && prevKey.length() >= 8) {
                            dlgAddGhost(row, "撤销这次导入", new View.OnClickListener() {
                                public void onClick(View v) {
                                    if (h[0] != null) h[0].dismiss();
                                    undoImport(prevKey, a.name);
                                }
                            }, true);
                        }
                        dlgAddGhost(row, "稍后", new View.OnClickListener() {
                            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
                        }, false);
                        c.addView(row);
                        h[0] = showCard(c);
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
