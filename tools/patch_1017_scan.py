# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()

def rep(old, new, cnt=1):
    global s
    assert old in s, "MISS: " + old[:80]
    s = s.replace(old, new, cnt)

# SAF 扫不到时回落到真实路径扫（MANAGE_EXTERNAL_STORAGE / 存储权限可用时）
rep('''                try {
                    String rootId = android.provider.DocumentsContract.getTreeDocumentId(tree);
                    walkTreeForKeys(tree, rootId, "", 0, found);
                } catch (Throwable t) {
                    log("[导入] 扫描失败：" + t);
                }''',
'''                try {
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
                }''')

rep('''    private String folderLabelOf(String path, String fileName) {''',
'''    /** 把 SAF 的 tree uri 换成 /sdcard 下的相对路径，失败返回 null。 */
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

    private String folderLabelOf(String path, String fileName) {''')

# 临时调试钩子（发布前删除）
rep('''    protected void onCreate(Bundle savedInstanceState) {''',
'''    private void dbgImportHook() {
        if (getIntent() == null) return;
        String t = getIntent().getStringExtra("testtree");
        if (t == null || t.length() == 0) return;
        final android.net.Uri u = android.net.Uri.parse(t);
        showPage(1);
        log("[test] 扫描 " + t);
        pool.execute(new Runnable() {
            public void run() {
                final java.util.List<FoundKey> found = new java.util.ArrayList<FoundKey>();
                try {
                    walkTreeForKeys(u, android.provider.DocumentsContract.getTreeDocumentId(u), "", 0, found);
                } catch (Throwable x) {
                    log("[test] SAF 失败：" + x);
                }
                if (found.isEmpty()) {
                    String rel = relPathOfTree(u);
                    if (rel != null) fileWalkForKeys(rel, found);
                }
                log("[test] 找到 " + found.size() + " 个");
                final java.util.List<FoundKey> ff = new java.util.ArrayList<FoundKey>();
                for (int i = 0; i < found.size(); i++) {
                    if (!libraryHasKey(found.get(i).key)) ff.add(found.get(i));
                    log("[test] " + found.get(i).name + " | " + hash(found.get(i).key).substring(0, 16) + " | " + found.get(i).path);
                }
                runOnUiThread(new Runnable() {
                    public void run() {
                        if (getIntent().getBooleanExtra("testauto", false)) {
                            if (ff.isEmpty()) toast("没有可导入的新 key");
                            else importFoundKeys(ff);
                        } else {
                            showImportFolderResult(u, treeLabel(u), found);
                        }
                    }
                });
            }
        });
    }

    protected void onCreate(Bundle savedInstanceState) {''')

io.open(P, "w", encoding="utf-8").write(s)
print("ok", len(s))
