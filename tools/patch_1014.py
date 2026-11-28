# -*- coding: utf-8 -*-
import io, sys, os
p = r"D:/123/4/android/src/com/housamo/authkey/MainActivity.java"
s = io.open(p, encoding="utf-8").read()
orig = s
def rep(old, new, tag):
    global s
    n = s.count(old)
    assert n == 1, "%s: count=%d" % (tag, n)
    s = s.replace(old, new, 1)
    print("ok", tag)

# 1) exportSub 一律返回游戏名
rep(u'''        /** 导出 / 备份目录里这个游戏用的子文件夹（东放沿用老路径，不加子目录）。 */
        String exportSub() {
            return "housamo".equals(id) ? "" : label;
        }''',
    u'''        /** 导出 / 备份目录里这个游戏用的子文件夹（每个游戏一个同名子目录）。 */
        String exportSub() {
            return label;
        }''', "exportSub")

# 2) exportedExists 兼容新旧路径
old_exported = u'''    /** 用 MediaStore 查 Download/东放Key/<名字>/AuthKey.txt 是否已存在。 */
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
    }'''
new_exported = u'''    /** 用 MediaStore / 文件系统查 <默认导出根>/[游戏名/]<名字>/AuthKey.txt 是否已存在。 */
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
    }'''
rep(old_exported, new_exported, "exportedExists")

# 3) scanExportRoot 重构（多根 + SAF 抽方法）
old_scan_start = u'''    private List<Account> scanExportRoot() {
        List<Account> out = new ArrayList<Account>();
        try {
            File root = exportRootGameDir();'''
i = s.find(old_scan_start)
assert i > 0, "scanExportRoot start not found"
end_marker = u'''        return out;
    }

    private int syncFromExportFolder() {'''
j = s.find(end_marker, i)
assert j > 0, "scanExportRoot end not found"
new_scan = u'''    private List<Account> scanExportRoot() {
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

'''
s = s[:i] + new_scan + s[j + len(u"        return out;\n    }\n\n") :]
print("ok scanExportRoot")

# 4) 备份目录按游戏分
rep(u'''    private String backupRootLabel() {
        String l = getPreferences(MODE_PRIVATE).getString("backupRootLabel", "");
        return l.length() == 0 ? "Download/东放Key/导入前备份/" : l;
    }''',
    u'''    /** 默认备份目录（带游戏子目录）的展示文案。 */
    private String backupDefaultLabel() {
        return exportRelPrefix() + "导入前备份/";
    }

    private String backupRootLabel() {
        String l = getPreferences(MODE_PRIVATE).getString("backupRootLabel", "");
        return l.length() == 0 ? backupDefaultLabel() : l;
    }''', "backupRootLabel")

rep(u'''    private String backupRootPath() {
        return Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS).getAbsolutePath()
                + "/东放Key/导入前备份";
    }''',
    u'''    private String backupRootPath() {
        return Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS).getAbsolutePath()
                + "/东放Key/" + game.exportSub() + "/导入前备份";
    }''', "backupRootPath")

rep(u'''        String rel = "Download/东放Key/导入前备份/" + name;''',
    u'''        String rel = backupDefaultLabel() + name;''', "backup rel")

rep(u'''                cv.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/东放Key/导入前备份");''',
    u'''                cv.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS + "/东放Key/" + game.exportSub() + "/导入前备份");''', "backup mediastore")

# 5) 设置页说明文案
rep(u'''        sh.setText("备份位置是每次导入前，自动把游戏里正在用的 key 存一份的地方。不换就存在 Download/东放Key/导入前备份/。");''',
    u'''        sh.setText("备份位置是每次导入前，自动把游戏里正在用的 key 存一份的地方。不换就存在 " + backupDefaultLabel() + "。");''', "settings text")

# 6) 版本号
rep(u'''    static final String CURRENT_VER = "1.0.13";''',
    u'''    static final String CURRENT_VER = "1.0.14";''', "CURRENT_VER")

io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("bytes", len(orig.encode("utf-8")), "->", len(s.encode("utf-8")))
