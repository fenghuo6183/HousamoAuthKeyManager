# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
orig = s

def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, ("anchor %d times: %r" % (s.count(old), old[:90]))
    s = s.replace(old, new, cnt)

# REQ_TREE_ZIP const
rep('    private static final int REQ_TREE_IMPORT = 0x74;',
    '    private static final int REQ_TREE_IMPORT = 0x74;\n    private static final int REQ_TREE_ZIP = 0x75;')

# refreshHomeOverview calls
rep('''                        curFp = f;
                        curKey = kk;
                        refreshAccountsView();''',
    '''                        curFp = f;
                        curKey = kk;
                        refreshAccountsView();
                        refreshHomeOverview();''')

# doImportNow: history capture
rep('''                final boolean[] backupOk = {true};
                String old = null;''',
    '''                final boolean[] backupOk = {true};
                String bakNameForHistory = null;
                String old = null;''')

rep('''                        if (already != null) {
                            log("[备份] 这个 key 已经备份过（" + already.name + "），跳过重复备份");
                        } else {''',
    '''                        if (already != null) {
                            log("[备份] 这个 key 已经备份过（" + already.name + "），跳过重复备份");
                            bakNameForHistory = already.name;
                        } else {''')

rep('''                        bak.folder = saved == null ? "" : saved;
                        runOnUiThread(new Runnable() {''',
    '''                        bak.folder = saved == null ? "" : saved;
                        bakNameForHistory = bak.name;
                        runOnUiThread(new Runnable() {''')

rep('''                                accounts.add(bak);
                                saveVault();
                                refreshList();''',
    '''                                accounts.add(bak);
                                saveVault();
                                pruneBackups();
                                refreshList();''')

rep('''                final String prevKey = old;
                // 2. 停止游戏''',
    '''                final String prevKey = old;
                final String histBackup = bakNameForHistory;
                if (prevKey != null && prevKey.length() >= 8) recordImportHistory(a.name, prevKey, histBackup);
                // 2. 停止游戏''')

# success dialog: add undo ghost
rep('''                        LinearLayout row = dlgBtnRow();
                        dlgAddGhost(row, "稍后", new View.OnClickListener() {
                            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
                        }, false);
                        c.addView(row);
                        h[0] = showCard(c);''',
    '''                        LinearLayout row = dlgBtnRow();
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
                        h[0] = showCard(c);''')

# settings card: backup & history
rep('''        LinearLayout about = card();
        about.addView(caption("关于"));''',
    '''        LinearLayout bh = card();
        bh.addView(caption("备份与历史"));
        rowKeepVal = value(0, keepLabel(backupKeep()));
        bh.addView(rowWith(rowKeepVal, "自动备份保留", new View.OnClickListener() {
            public void onClick(View v) { chooseBackupKeep(); }
        }));
        bh.addView(divider());
        bh.addView(rowWith(value(0, "看每一次导入前的 key"), "导入历史", new View.OnClickListener() {
            public void onClick(View v) { showImportHistory(); }
        }));
        TextView bhh = new TextView(this);
        bhh.setText("自动备份是每次导入前，把游戏里正在用的 key 存下的那一份。默认全部保留。");
        bhh.setTextSize(11);
        bhh.setTextColor(Color.parseColor("#9AA3B0"));
        bhh.setPadding(dp(2), dp(10), dp(2), dp(2));
        bh.addView(bhh);
        p.addView(bh, cardParams(0));

        LinearLayout about = card();
        about.addView(caption("关于"));''')

# field for keep value
rep('    private TextView rowHomeFp, rowHomeBak, rowHomeCnt;',
    '    private TextView rowHomeFp, rowHomeBak, rowHomeCnt;\n    private TextView rowKeepVal;')

# new methods: insert before addAccount
anchor = '    private void addAccount(String name, String key, String source) {'
methods = '''    // ---------- 导入历史 / 备份保留 / 撤销 / 打包导出 ----------

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

    private void recordImportHistory(String toName, String prevKey, String backupName) {
        try {
            SharedPreferences sp = getPreferences(MODE_PRIVATE);
            String raw = sp.getString("importHistory", "[]");
            JSONArray arr = new JSONArray(raw);
            JSONObject o = new JSONObject();
            o.put("t", stamp());
            o.put("to", toName);
            o.put("prevFp", hash(prevKey).substring(0, 16));
            o.put("toFp", hash(toName).length());
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
                    man.append("Housamo AuthKey Manager\\n");
                    man.append("游戏: ").append(game.label).append("\\n");
                    man.append("时间: ").append(stamp()).append("\\n");
                    man.append("说明: 每个子文件夹里的 AuthKey.txt 就是一个账号的 key。\\n\\n");
                    man.append("文件夹\\t指纹\\t大小\\t创建时间\\t备注\\n");
                    for (Account a : accounts) {
                        if (!inGame(a) || a.isBackup()) continue;
                        String dir = safeName(a.name);
                        zos.putNextEntry(new java.util.zip.ZipEntry(dir + "/AuthKey.txt"));
                        zos.write(a.key.getBytes("UTF-8"));
                        zos.closeEntry();
                        man.append(dir).append("\\t").append(a.fpShort()).append("\\t")
                                .append(a.key.length()).append("B\\t").append(a.created).append("\\t")
                                .append(a.note == null ? "" : a.note).append("\\n");
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

'''
rep(anchor, methods + anchor)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched", len(orig), "->", len(s))
