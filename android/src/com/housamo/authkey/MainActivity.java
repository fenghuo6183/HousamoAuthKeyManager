package com.housamo.authkey;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
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
    private TextView tvLog;
    private ScrollView logScroll;
    private ListView list;
    private ArrayAdapter<String> adapter;
    private final List<Account> accounts = new ArrayList<Account>();
    private final ExecutorService pool = Executors.newSingleThreadExecutor();
    private boolean rootChecked = false;
    private boolean hasRoot = false;

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
        pool.execute(new Runnable() {
            public void run() {
                hasRoot = checkRoot();
                rootChecked = true;
                runOnUiThread(new Runnable() {
                    public void run() {
                        updateState();
                    }
                });
                log(hasRoot ? "[root] 已获取 root 权限，可直接读写游戏私有目录。" : "[root] 未获取 root：Android 11+ 无法访问游戏数据目录，请改用 Windows 版（adb 无需 root）。");
                String found = findGamePackages();
                log("[游戏] 检测到的相关包名：" + (found.length() == 0 ? "无（确认游戏装在同一台手机上）" : found));
                log("[游戏] 数据目录 " + EXT_DIR + "：" + (new File(EXT_DIR).exists() ? "存在" : "不存在或无权访问"));
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
        root.setPadding(dp(12), dp(12), dp(12), dp(8));
        root.setBackgroundColor(Color.parseColor("#F5F6F8"));

        TextView title = new TextView(this);
        title.setText("东放 Key 管家");
        title.setTextSize(20);
        title.setTextColor(Color.parseColor("#1B1F24"));
        title.setGravity(Gravity.CENTER);
        root.addView(title);

        tvState = new TextView(this);
        tvState.setTextSize(12);
        tvState.setTextColor(Color.parseColor("#5B6470"));
        tvState.setPadding(0, dp(6), 0, dp(6));
        root.addView(tvState);

        LinearLayout row0 = new LinearLayout(this);
        row0.setOrientation(LinearLayout.HORIZONTAL);
        Button bRefresh = mkBtn("刷新状态");
        bRefresh.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                updateState();
                refreshList();
            }
        });
        Button bPerm = mkBtn("存储权限");
        bPerm.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                askStorage();
            }
        });
        row0.addView(bRefresh, weight());
        row0.addView(bPerm, weight());
        root.addView(row0);

        list = new ListView(this);
        list.setChoiceMode(ListView.CHOICE_MODE_SINGLE);
        adapter = new ArrayAdapter<String>(this, android.R.layout.simple_list_item_single_choice, new ArrayList<String>());
        list.setAdapter(adapter);
        list.setOnItemClickListener(new AdapterView.OnItemClickListener() {
            public void onItemClick(AdapterView<?> p, View v, int pos, long id) {
                updateState();
            }
        });
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f);
        root.addView(list, lp);

        LinearLayout row1 = new LinearLayout(this);
        row1.setOrientation(LinearLayout.HORIZONTAL);
        Button bExtract = mkBtn("提取当前 Key");
        bExtract.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                doExtract();
            }
        });
        Button bImport = mkBtn("导入选中");
        bImport.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                doImport();
            }
        });
        row1.addView(bExtract, weight());
        row1.addView(bImport, weight());
        root.addView(row1);

        LinearLayout row2 = new LinearLayout(this);
        row2.setOrientation(LinearLayout.HORIZONTAL);
        Button bCopy = mkBtn("复制");
        bCopy.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                doCopy();
            }
        });
        Button bRename = mkBtn("重命名");
        bRename.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                doRename();
            }
        });
        Button bDel = mkBtn("删除");
        bDel.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                doDelete();
            }
        });
        row2.addView(bCopy, weight());
        row2.addView(bRename, weight());
        row2.addView(bDel, weight());
        root.addView(row2);

        TextView tip = new TextView(this);
        tip.setTextSize(11);
        tip.setTextColor(Color.parseColor("#8A929B"));
        tip.setPadding(0, dp(4), 0, dp(4));
        tip.setText("提示：导入前会先停游戏并备份当前 Key；账号库仅存本机。");
        root.addView(tip);

        logScroll = new ScrollView(this);
        tvLog = new TextView(this);
        tvLog.setTextSize(11);
        tvLog.setTextColor(Color.parseColor("#3A424B"));
        tvLog.setTypeface(android.graphics.Typeface.MONOSPACE);
        tvLog.setMovementMethod(new ScrollingMovementMethod());
        logScroll.addView(tvLog);
        root.addView(logScroll, new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(110)));
        return root;
    }

    private Button mkBtn(String text) {
        Button b = new Button(this);
        b.setText(text);
        b.setAllCaps(false);
        b.setTextSize(13);
        return b;
    }

    private LinearLayout.LayoutParams weight() {
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        p.setMargins(dp(3), dp(3), dp(3), dp(3));
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
        StringBuilder sb = new StringBuilder();
        if (!rootChecked) sb.append("root 检测中…  ");
        else sb.append(hasRoot ? "root：已授权  " : "root：未授权  ");
        sb.append(gameInstalled ? "游戏：已检测到  " : "游戏：未检测到  ");
        if (hasRoot) sb.append("root 已授权  ");
        sb.append("已选：").append(list.getCheckedItemPosition() >= 0 ? accounts.get(list.getCheckedItemPosition()).name : "无");
        tvState.setText(sb.toString());
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
        Res r = su("cat '" + path + "' 2>/dev/null", 15000);
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
                    log("[失败] 未找到 AuthKey。请确认游戏已登录至少一次；Android 11+ 需要 root 或改用 Windows 版。");
                    toast("未找到 AuthKey");
                    return;
                }
                final Account a = new Account("设备 " + Build.MODEL + " " + stamp(), key);
                a.note = "来源：" + (found == null ? "?" : found);
                runOnUiThread(new Runnable() {
                    public void run() {
                        accounts.add(a);
                        saveVault();
                        refreshList();
                        list.setItemChecked(accounts.size() - 1, true);
                    }
                });
                log("[成功] 已提取并加入账号库：" + a.name + " (" + a.fp() + ")");
                toast("已提取");
            }
        });
    }

    private byte[] scanByFind() {
        if (!hasRoot) return null;
        Res r = su("find /sdcard /data/data/" + PKG + " -name AuthKey -type f 2>/dev/null | head -5", 25000);
        String s = new String(r.out).trim();
        if (s.length() == 0) return null;
        String first = s.split("\n")[0].trim();
        log("[扫描] 找到文件：" + first);
        return readKeyAt(first);
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
                if (hasRoot) {
                    su("am force-stop " + PKG, 15000);
                } else {
                    su("am force-stop " + PKG, 8000);
                }
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
