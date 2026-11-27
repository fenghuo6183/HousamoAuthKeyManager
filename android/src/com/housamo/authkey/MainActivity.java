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

    static final String PKG = "jp.co.lifewonders.housamo";
    static final String EXT_DIR = "/sdcard/Android/data/" + PKG + "/files/Data";
    static final String EXT_KEY = EXT_DIR + "/AuthKey";
    static final String PREFS1 = "/data/data/" + PKG + "/shared_prefs/" + PKG + ".v2.playerprefs.xml";
    static final String PREFS2 = "/data/user/0/" + PKG + "/shared_prefs/" + PKG + ".v2.playerprefs.xml";
    static final String VAULT = "vault";
    static final String VAULT_KEY = "accounts";

    private TextView tvState;
    private LinearLayout host, pageHome, pageTask, pageAcc, pageSet;
    private TextView tabHome, tabTask, tabAcc, tabSet;
    private TextView rowRootVal, rowGameVal, rowShzkVal, rowPermVal, rowCount, rowSaved, rowSelVal;
    private TextView rowStoreVal, rowResVal, rowOsVal, rowVerVal;
    private TextView rowSvcVal, rowModeVal, rowBatteryVal, rowNotifVal, rowGameVerVal, rowExportVal, rowUpdateVal;
    private static final int REQ_TREE = 0x71;
    private TextView tvLog;
    private ScrollView logScroll;
    private ListView list;
    private AccountAdapter adapter;
    private final List<Account> accounts = new ArrayList<Account>();
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

        Account() {
        }

        Account(String n, String k) {
            name = n;
            key = k;
            created = stamp();
        }

        String fp() {
            if (key.length() <= 20) return "短key(" + key.length() + ")";
            return hash(key).substring(0, 16) + " | " + key.length() + "B";
        }

        JSONObject toJson() throws Exception {
            JSONObject o = new JSONObject();
            o.put("name", name);
            o.put("note", note);
            o.put("key", key);
            o.put("created", created);
            o.put("folder", folder);
            return o;
        }

        static Account fromJson(JSONObject o) {
            Account a = new Account();
            a.name = o.optString("name", "");
            a.note = o.optString("note", "");
            a.key = o.optString("key", "");
            a.created = o.optString("created", "");
            a.folder = o.optString("folder", "");
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

    // ---------- 生命周期 ----------

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(buildUi());
        loadVault();
        refreshList();
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
        sub.setText("导入 / 导出 / 日志 都在这里");
        sub.setTextSize(12);
        sub.setTextColor(Color.parseColor("#9AA3B0"));
        sub.setPadding(dp(2), 0, 0, dp(8));
        p.addView(sub);

        LinearLayout sv = card();
        sv.addView(caption("存到哪个文件夹"));
        rowSaved = value(0, exportRootLabel());
        sv.addView(rowWith(rowSaved, "点此选择文件夹", new View.OnClickListener() {
            public void onClick(View v) { chooseExportDir(); }
        }));
        TextView hint = new TextView(this);
        hint.setText("提取完会让你起一个名字，key 自动存成 选中文件夹/名字/AuthKey.txt，不用再点导出。");
        hint.setTextSize(11);
        hint.setTextColor(Color.parseColor("#9AA3B0"));
        hint.setPadding(dp(2), dp(2), 0, dp(4));
        sv.addView(hint);
        p.addView(sv, cardParams(0));

        LinearLayout cur = card();
        rowSelVal = value(0, "未选择");
        cur.addView(rowWith(rowSelVal, "当前账号", new View.OnClickListener() {
            public void onClick(View v) { showPage(2); }
        }));
        TextView ch = new TextView(this);
        ch.setText("点这一行去「账号」页挑一个 key，下面就能导入到游戏");
        ch.setTextSize(11);
        ch.setTextColor(Color.parseColor("#9AA3B0"));
        ch.setPadding(dp(2), dp(2), 0, dp(4));
        cur.addView(ch);
        p.addView(cur, cardParams(0));

        p.addView(taskCard("提取当前账号的 key", "把游戏里正在登录的账号 key 抽出来，存进账号库，并自动存一份到上面选的文件夹。", new View.OnClickListener() {
            public void onClick(View v) { doExtract(); }
        }), cardParams(0));

        p.addView(taskCard("将当前选择的 key 导入到游戏", "先停掉游戏、把游戏原来的 key 备份一份，再写入你选的 key，写完回读核对。", new View.OnClickListener() {
            public void onClick(View v) { doImport(); }
        }), cardParams(0));

        p.addView(taskCard("把选中的 key 再存一份到文件夹", "不想重安装游戏、只想把 key 导出成文件时用。", new View.OnClickListener() {
            public void onClick(View v) { doExport(); }
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
        tvState.setPadding(dp(2), 0, 0, dp(6));
        p.addView(tvState);

        LinearLayout ac = card();
        list = new ListView(this);
        list.setChoiceMode(ListView.CHOICE_MODE_SINGLE);
        list.setDivider(null);
        list.setSelector(roundRect(Color.parseColor("#EEF3FF"), 10, 0, 0));
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
                doCopy();
                return true;
            }
        });
        ac.addView(list, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f));
        p.addView(ac, cardParams(1));

        LinearLayout op = card();
        LinearLayout row1 = new LinearLayout(this);
        row1.setOrientation(LinearLayout.HORIZONTAL);
        Button bCopy = mkBtn("复制", false);
        bCopy.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { doCopy(); }
        });
        Button bRename = mkBtn("重命名", false);
        bRename.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { doRename(); }
        });
        Button bDel = mkBtn("删除", false);
        bDel.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { doDelete(); }
        });
        row1.addView(bCopy, weight());
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
        exp.addView(caption("导出"));
        rowExportVal = value(0, exportRootLabel());
        exp.addView(rowWith(rowExportVal, "导出位置（点此选择文件夹）", new View.OnClickListener() {
            public void onClick(View v) { chooseExportDir(); }
        }));
        exp.addView(divider());
        exp.addView(rowWith(value(0, "每个账号一个子文件夹，里面是 AuthKey.txt"), "结构", null));
        p.addView(exp, cardParams(0));

        LinearLayout about = card();
        about.addView(caption("关于"));
        about.addView(rowWith(value(0, "1.0.5"), "版本", null));
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
        public int getCount() { return accounts.size(); }
        public Object getItem(int i) { return accounts.get(i); }
        public long getItemId(int i) { return i; }

        public View getView(int pos, View convert, ViewGroup parent) {
            LinearLayout row = new LinearLayout(MainActivity.this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setGravity(Gravity.CENTER_VERTICAL);
            row.setPadding(dp(10), dp(11), dp(12), dp(11));
            Account a = accounts.get(pos);
            boolean on = list != null && list.getCheckedItemPosition() == pos;

            LinearLayout col = new LinearLayout(MainActivity.this);
            col.setOrientation(LinearLayout.VERTICAL);
            TextView name = new TextView(MainActivity.this);
            name.setText((pos + 1) + ". " + a.name);
            name.setTextSize(14);
            name.setTextColor(Color.parseColor("#101418"));
            TextView sub = new TextView(MainActivity.this);
            sub.setText(a.fp() + "  \u00B7  " + a.created);
            sub.setTextSize(11);
            sub.setTextColor(Color.parseColor("#8A93A0"));
            sub.setPadding(0, dp(2), 0, 0);
            TextView path = new TextView(MainActivity.this);
            boolean exported = a.folder != null && a.folder.length() > 0;
            path.setText(exported ? a.folder : expectedPath(a.name) + "（未导出，任务页可导出）");
            path.setTextSize(10);
            path.setTextColor(Color.parseColor(exported ? "#7C8794" : "#B9C0CB"));
            path.setPadding(0, dp(2), 0, 0);
            col.addView(name);
            col.addView(sub);
            col.addView(path);

            TextView dot = new TextView(MainActivity.this);
            dot.setText(on ? "\u25CF" : "\u25CB");
            dot.setTextSize(15);
            dot.setTextColor(Color.parseColor(on ? "#2F6BFF" : "#C9D0DA"));
            dot.setPadding(dp(8), 0, 0, 0);

            row.addView(col, new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f));
            row.addView(dot);
            return row;
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
            rowGameVal.setText(gameInstalled ? "已检测到" : "未检测到");
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
        if (rowCount != null) rowCount.setText(accounts.size() + " 个");
        if (tvState != null) {
            Account a = selected();
            tvState.setText(a == null ? "已选：无" : "已选：" + a.name + "  ·  " + a.fp());
        }
        if (adapter != null) adapter.notifyDataSetChanged();
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
        int p = list.getCheckedItemPosition();
        if (p < 0 || p >= accounts.size()) return null;
        return accounts.get(p);
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
            if (a.folder == null || a.folder.length() == 0) {
                if (exportedExists(a.name)) {
                    a.folder = "/storage/emulated/0/Download/东放Key/" + safeName(a.name) + "/AuthKey.txt";
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
        a.note = "来源：" + source;
        accounts.add(a);
        saveVault();
        refreshList();
        list.setItemChecked(accounts.size() - 1, true);
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
                final String rel = url == null ? "https://github.com/fenghuo6183/HousamoAuthKeyManager/releases" : url;
                final int cmp = ver.length() == 0 ? 0 : compareVer(ver, "1.0.5");
                runOnUiThread(new Runnable() {
                    public void run() {
                        if (rowUpdateVal != null) {
                            rowUpdateVal.setText(cmp > 0 ? "发现 " + ver + "，点此下载" : "已是最新版 1.0.5");
                            rowUpdateVal.setTextColor(cmp > 0 ? Color.parseColor("#2F6BFF") : Color.parseColor("#9AA3B0"));
                        }
                        if (cmp > 0) {
                            log("[更新] 发现新版本 " + ver + "，点「检查更新」下载");
                            toast("发现新版本 " + ver);
                            if (rowUpdateVal != null) {
                                rowUpdateVal.setOnClickListener(new View.OnClickListener() {
                                    public void onClick(View v) { openUrl(rel); }
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
        if (req != REQ_TREE || res != RESULT_OK || data == null || data.getData() == null) return;
        android.net.Uri uri = data.getData();
        try {
            getContentResolver().takePersistableUriPermission(uri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        } catch (Throwable ignored) {
        }
        String label = uri.getLastPathSegment();
        if (label == null) label = uri.toString();
        int c = label.indexOf(':');
        if (c >= 0) label = label.substring(c + 1);
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
        android.net.Uri tree = exportRootUri();
        if (tree != null) {
            String t = exportToTree(tree, safe, data);
            if (t != null) return exportRootLabel() + "/" + safe + "/AuthKey.txt";
        }
        String rel = Environment.DIRECTORY_DOWNLOADS + "/东放Key/" + safe;
        // 1) 直接写（Android 10 及以下，或已授予「所有文件访问」）
        try {
            File dir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "东放Key/" + safe);
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
            Res r = shWithInput("mkdir -p '/sdcard/Download/东放Key/" + safe + "' && cat > '/sdcard/Download/东放Key/"
                    + safe + "/AuthKey.txt'", data, 20000);
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

    private void doCopy() {
        Account a = selected();
        if (a == null) {
            toast("请先选中一个账号");
            return;
        }
        ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
        cm.setPrimaryClip(ClipData.newPlainText("AuthKey", a.key));
        log("[复制] 已复制 " + a.name + " 的 Key 到剪贴板");
        toast("已复制");
    }

    private void doRename() {
        final Account a = selected();
        if (a == null) {
            toast("请先选中一个账号");
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
                .setTitle("删除账号")
                .setMessage("确定删除「" + a.name + "」？此操作不可撤销。")
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

    private void doImport() {
        final Account a = selected();
        if (a == null) {
            toast("请先选中一个账号");
            return;
        }
        log("--- 开始导入：" + a.name + " ---");
        pool.execute(new Runnable() {
            public void run() {
                // 1. 备份现有 key
                String old = null;
                byte[] cur = readKeyAt(EXT_KEY);
                if (cur == null) cur = readKeyAt(PREFS1);
                if (cur != null) {
                    old = new String(cur).trim();
                    if (old.length() >= 8) {
                        final Account bak = new Account("自动备份 " + stamp(), old);
                        bak.note = "导入「" + a.name + "」前自动备份";
                        runOnUiThread(new Runnable() {
                            public void run() {
                                accounts.add(bak);
                                saveVault();
                                refreshList();
                            }
                        });
                        log("[备份] 已备份当前 Key → " + bak.name);
                    }
                }
                // 2. 停止游戏
                shell("am force-stop " + PKG, 15000);
                log("[停止] 已尝试停止游戏进程");
                // 3. 写入
                boolean ok = writeKey(a.key.getBytes());
                if (!ok) {
                    log("[失败] 写入 AuthKey 失败。Android 11+ 需要 root；也可改用 Windows 版。");
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
                toast("导入完成");
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
