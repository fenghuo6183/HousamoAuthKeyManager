# -*- coding: utf-8 -*-
import io, re, sys

P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
orig = s

# 1) 新增 REQ 码
s = s.replace("""    private static final int REQ_TREE_BAK = 0x73;""",
"""    private static final int REQ_TREE_BAK = 0x73;
    private static final int REQ_TREE_IMPORT = 0x74;""", 1)

# 2) onActivityResult：放行新 req + 分支
s = s.replace("""        if (req != REQ_TREE && req != REQ_TREE_COPY && req != REQ_TREE_BAK) return;""",
"""        if (req != REQ_TREE && req != REQ_TREE_COPY && req != REQ_TREE_BAK && req != REQ_TREE_IMPORT) return;""", 1)

s = s.replace("""        if (req == REQ_TREE_COPY) {
            Account a = copyTarget;""",
"""        if (req == REQ_TREE_IMPORT) {
            scanFolderForKeys(uri);
            return;
        }
        if (req == REQ_TREE_COPY) {
            Account a = copyTarget;""", 1)

# 3) 任务页卡片
s = s.replace("""        p.addView(taskCard("把选中的 key 复制到其他文件夹", "复制一份到你指定的文件夹（备份到别处、发给另一台设备都行）；选「移动」的话，复制完会把原来导出文件夹里的那份删掉。", new View.OnClickListener() {
            public void onClick(View v) { startCopyMove(); }
        }), cardParams(0));""",
"""        p.addView(taskCard("把选中的 key 复制到其他文件夹", "复制一份到你指定的文件夹（备份到别处、发给另一台设备都行）；选「移动」的话，复制完会把原来导出文件夹里的那份删掉。", new View.OnClickListener() {
            public void onClick(View v) { startCopyMove(); }
        }), cardParams(0));

        p.addView(taskCard("从一个文件夹导入 key", "选一个文件夹，把它（含子文件夹）里的 AuthKey 全部加进账号库，只是进「账号」分段，不会碰游戏里现在登录的账号。", new View.OnClickListener() {
            public void onClick(View v) { startImportFolder(); }
        }), cardParams(0));""", 1)

METHODS = r'''
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
                    log("[导入] 扫描失败：" + t);
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
            dlgPrimary(c, "知道了", new View.OnClickListener() {
                public void onClick(View v) { dismissCard(v); }
            });
            showCard(c);
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
        listTv.setTextColor(Color.parseColor("#4B5563"));
        listTv.setLineSpacing(dp(4), 1f);
        listTv.setTypeface(android.graphics.Typeface.MONOSPACE);
        listTv.setPadding(0, dp(6), 0, dp(2));
        c.addView(listTv);
        dlgPrimary(c, "全部导入（" + fresh.size() + " 个）", new View.OnClickListener() {
            public void onClick(View v) {
                dismissCard(v);
                importFoundKeys(fresh);
            }
        });
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "取消", new View.OnClickListener() {
            public void onClick(View v) { dismissCard(v); }
        }, false);
        c.addView(row);
        showCard(c);
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
        dlgPrimary(c, "去看看账号", new View.OnClickListener() {
            public void onClick(View v) {
                dismissCard(v);
                showPage(2);
            }
        });
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "先这样", new View.OnClickListener() {
            public void onClick(View v) { dismissCard(v); }
        }, false);
        c.addView(row);
        showCard(c);
    }
'''

anchor = """    private void addAccount(String name, String key, String source) {"""
assert anchor in s
s = s.replace(anchor, METHODS.strip("\n") + "\n\n" + anchor, 1)

s = s.replace('static final String CURRENT_VER = "1.0.16";', 'static final String CURRENT_VER = "1.0.17";', 1)

io.open(P, "w", encoding="utf-8").write(s)
print("patched", len(orig), "->", len(s))

M = "android/AndroidManifest.xml"
t = io.open(M, encoding="utf-8").read()
t = t.replace('android:versionCode="17"', 'android:versionCode="18"').replace('android:versionName="1.0.16"', 'android:versionName="1.0.17"')
io.open(M, "w", encoding="utf-8").write(t)
print("manifest ok")

B = "android/build_apk.py"
b = io.open(B, encoding="utf-8").read()
b = b.replace('VERSION_CODE = "17"', 'VERSION_CODE = "18"').replace('VERSION_NAME = "1.0.16"', 'VERSION_NAME = "1.0.17"')
io.open(B, "w", encoding="utf-8").write(b)
print("build ok")
