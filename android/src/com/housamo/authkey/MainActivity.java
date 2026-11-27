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
    private LinearLayout host, pageHome, pageAcc, pageSet;
    private TextView tabHome, tabAcc, tabSet;
    private TextView rowRootVal, rowGameVal, rowShzkVal, rowPermVal, rowCount, rowSaved;
    private TextView tvLog;
    private ScrollView logScroll;
    private ListView list;
    private ArrayAdapter<String> adapter;
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
            return o;
        }

        static Account fromJson(JSONObject o) {
            Account a = new Account();
            a.name = o.optString("name", "");
            a.note = o.optString("note", "");
            a.key = o.optString("key", "");
            a.created = o.optString("created", "");
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
        pool.execute(new Runnable() {
            public void run() {
                hasRoot = checkRoot();
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
                String found = findGamePackages();
                log("[游戏] 检测到的相关包名：" + (found.length() == 0 ? "无（确认游戏装在同一台手机上）" : found));
                log("[游戏] 数据目录 " + EXT_DIR + "：" + (new File(EXT_DIR).exists() ? "存在" : "App 无权直接访问（Android 11+ 正常，走 Shizuku/root 通道）"));
            }
        });
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
        pageAcc = buildAccounts();
        pageSet = buildSettings();
        host.addView(pageHome, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        host.addView(pageAcc, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        host.addView(pageSet, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        View line = new View(this);
        line.setBackgroundColor(Color.parseColor("#E6E9EF"));
        root.addView(line, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(1)));

        LinearLayout nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        nav.setBackgroundColor(Color.WHITE);
        nav.setPadding(0, dp(6), 0, dp(6));
        tabHome = mkTab("任务");
        tabAcc = mkTab("账号");
        tabSet = mkTab("设置");
        tabHome.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { showPage(0); }
        });
        tabAcc.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { showPage(1); }
        });
        tabSet.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { showPage(2); }
        });
        nav.addView(tabHome, weightNav());
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

    private void showPage(int idx) {
        if (pageHome == null) return;
        pageHome.setVisibility(idx == 0 ? View.VISIBLE : View.GONE);
        pageAcc.setVisibility(idx == 1 ? View.VISIBLE : View.GONE);
        pageSet.setVisibility(idx == 2 ? View.VISIBLE : View.GONE);
        int on = Color.parseColor("#2F6BFF");
        int off = Color.parseColor("#9AA3B0");
        tabHome.setTextColor(idx == 0 ? on : off);
        tabAcc.setTextColor(idx == 1 ? on : off);
        tabSet.setTextColor(idx == 2 ? on : off);
        tabHome.setTypeface(null, idx == 0 ? android.graphics.Typeface.BOLD : android.graphics.Typeface.NORMAL);
        tabAcc.setTypeface(null, idx == 1 ? android.graphics.Typeface.BOLD : android.graphics.Typeface.NORMAL);
        tabSet.setTypeface(null, idx == 2 ? android.graphics.Typeface.BOLD : android.graphics.Typeface.NORMAL);
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
        p.addView(pageTitle("任务"));
        TextView sub = new TextView(this);
        sub.setText("提取 / 导入 / 导出");
        sub.setTextSize(12);
        sub.setTextColor(Color.parseColor("#9AA3B0"));
        sub.setPadding(dp(2), 0, 0, dp(8));
        p.addView(sub);

        LinearLayout st = card();
        rowRootVal = value(0, "检测中…");
        rowGameVal = value(0, "检测中…");
        rowShzkVal = value(0, "未连接");
        st.addView(rowWith(rowRootVal, "Root 权限", null));
        st.addView(divider());
        st.addView(rowWith(rowGameVal, "游戏", null));
        st.addView(divider());
        st.addView(rowWith(rowShzkVal, "Shizuku", new View.OnClickListener() {
            public void onClick(View v) { askShizuku(); }
        }));
        p.addView(st, cardParams(0));

        LinearLayout sv = card();
        rowSaved = value(0, "Download/东放Key/");
        sv.addView(rowWith(rowSaved, "导出的位置", null));
        TextView hint = new TextView(this);
        hint.setText("提取后可以自己命名，key 会存成 名字/AuthKey.txt");
        hint.setTextSize(11);
        hint.setTextColor(Color.parseColor("#9AA3B0"));
        hint.setPadding(dp(2), dp(8), 0, 0);
        sv.addView(hint);
        p.addView(sv, cardParams(0));

        LinearLayout op = card();
        Button bExtract = mkBtn("提取当前 Key", true);
        bExtract.setTextSize(15);
        bExtract.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { doExtract(); }
        });
        Button bImport = mkBtn("导入选中到游戏", false);
        bImport.setTextSize(15);
        bImport.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { doImport(); }
        });
        op.addView(bExtract, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        LinearLayout.LayoutParams ip = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        ip.setMargins(0, dp(8), 0, 0);
        op.addView(bImport, ip);
        Button bExport = mkBtn("导出选中到文件夹", false);
        bExport.setTextSize(15);
        bExport.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) { doExport(); }
        });
        LinearLayout.LayoutParams ep = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        ep.setMargins(0, dp(8), 0, 0);
        op.addView(bExport, ep);
        p.addView(op, cardParams(0));

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
        adapter = new ArrayAdapter<String>(this, android.R.layout.simple_list_item_single_choice, new ArrayList<String>());
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

        LinearLayout about = card();
        about.addView(caption("关于"));
        about.addView(rowWith(value(0, "1.0.3"), "版本", null));
        about.addView(divider());
        about.addView(rowWith(value(0, "GitHub"), "项目主页", new View.OnClickListener() {
            public void onClick(View v) {
                openUrl("https://github.com/fenghuo6183/HousamoAuthKeyManager");
            }
        }));
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
        if (rowPermVal != null) {
            rowPermVal.setText(!alive ? "未连接" : (granted ? "已授权" : "点此授权"));
            rowPermVal.setTextColor(!alive ? noColor : (granted ? okColor : grayColor));
        }
        if (rowCount != null) rowCount.setText(accounts.size() + " 个");
        if (tvState != null) {
            Account a = selected();
            tvState.setText(a == null ? "已选：无" : "已选：" + a.name + "  ·  " + a.fp());
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
        adapter.clear();
        for (int i = 0; i < accounts.size(); i++) {
            Account a = accounts.get(i);
            adapter.add((i + 1) + ". " + a.name + "\n    " + a.fp() + "  ·  " + a.created + (a.note.length() > 0 ? "\n    " + a.note : ""));
        }
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
            log("[导出] " + out);
            toast("已保存并导出");
        } else {
            log("[导出] 写 Download 失败：可点「存储权限」授权后再导一次。");
            toast("已保存（导出失败）");
        }
    }

    /** 把 key 原样写进 Download/东放Key/<名字>/AuthKey.txt，返回可读路径或 null。 */
    private String exportKeyFolder(String name, String key) {
        StringBuilder nb = new StringBuilder();
        for (int i = 0; i < name.length(); i++) {
            char c = name.charAt(i);
            if (Character.isLetterOrDigit(c) || c == ' ' || c == '-' || c == '_' || c == '.') nb.append(c);
            else nb.append('_');
        }
        String safe = nb.toString().trim();
        if (safe.length() == 0) safe = "账号";
        if (safe.length() > 40) safe = safe.substring(0, 40);
        byte[] data = key.getBytes();
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
