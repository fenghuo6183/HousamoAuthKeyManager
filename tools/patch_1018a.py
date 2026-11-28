# -*- coding: utf-8 -*-
import io, sys, re
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
orig = s

def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, ("anchor %d times: %r" % (s.count(old), old[:80]))
    s = s.replace(old, new, cnt)

# 1) count bug
rep('if (rowCount != null) rowCount.setText(countAccounts() + " 个账号 · " + countBackups() + " 个备份");',
    'if (rowCount != null) rowCount.setText(countAccounts() + " 个账号 · " + (countBackups() + countExportEntries()) + " 个备份");')

# 2) new fields
rep('    private int curPage = 0;\n',
    '    private int curPage = 0;\n'
    '    private TextView rowHomeFp, rowHomeBak, rowHomeCnt;\n')

# 3) home overview card
rep('        LinearLayout mode = card();\n        rowModeVal = value(0, "检测中...");',
    '        LinearLayout ov = card();\n'
    '        ov.addView(caption("账号概览"));\n'
    '        rowHomeFp = value(0, "读取中…");\n'
    '        ov.addView(rowWith(rowHomeFp, "游戏里现在用的 key", new View.OnClickListener() {\n'
    '            public void onClick(View v) {\n'
    '                curFpLoaded = false;\n'
    '                refreshCurrentFp();\n'
    '            }\n'
    '        }));\n'
    '        ov.addView(divider());\n'
    '        rowHomeBak = value(0, "—");\n'
    '        ov.addView(rowWith(rowHomeBak, "上次自动备份", null));\n'
    '        ov.addView(divider());\n'
    '        rowHomeCnt = value(0, "—");\n'
    '        ov.addView(rowWith(rowHomeCnt, "账号库", new View.OnClickListener() {\n'
    '            public void onClick(View v) { showPage(2); }\n'
    '        }));\n'
    '        p.addView(ov, cardParams(0));\n\n'
    '        LinearLayout mode = card();\n        rowModeVal = value(0, "检测中...");')

# 4) task page: clipboard + zip cards
rep('        LinearLayout lg = card();\n        lg.addView(caption("运行日志"));',
    '        p.addView(taskCard("从剪贴板导入 key", "先把 key（或整段 playerprefs xml）复制到剪贴板，点这里取出来存进账号库，不碰游戏。", new View.OnClickListener() {\n'
    '            public void onClick(View v) { importFromClipboard(); }\n'
    '        }), cardParams(0));\n\n'
    '        p.addView(taskCard("打包导出全部 key", "选一个文件夹，把账号库里这个游戏的 key 全打成一个 zip（含 manifest），换机备份一次带走。", new View.OnClickListener() {\n'
    '            public void onClick(View v) { startZipExport(); }\n'
    '        }), cardParams(0));\n\n'
    '        LinearLayout lg = card();\n        lg.addView(caption("运行日志"));')

# 5) account page: import entry
rep('        p.addView(rf, cardParams(0));',
    '        rf.addView(divider());\n'
    '        rf.addView(rowWith(value(0, "选一个文件夹，批量加进账号库"), "从文件夹导入 key", new View.OnClickListener() {\n'
    '            public void onClick(View v) { startImportFolder(); }\n'
    '        }));\n'
    '        p.addView(rf, cardParams(0));')

# 6) adapter: show note
rep('            col.addView(name);\n            col.addView(meta);\n            col.addView(path);\n',
    '            col.addView(name);\n            col.addView(meta);\n            col.addView(path);\n'
    '            String nnote = a.note == null ? "" : a.note.trim();\n'
    '            if (nnote.length() > 0 && !nnote.startsWith("来源：") && !nnote.startsWith("从文件夹导入：")\n'
    '                    && !nnote.startsWith("导入「") && !nnote.startsWith("导入到「")) {\n'
    '                TextView nt = new TextView(MainActivity.this);\n'
    '                nt.setText("备注 " + nnote);\n'
    '                nt.setTextSize(11);\n'
    '                nt.setSingleLine(true);\n'
    '                nt.setEllipsize(android.text.TextUtils.TruncateAt.END);\n'
    '                nt.setTextColor(Color.parseColor("#5B6572"));\n'
    '                nt.setPadding(0, dp(3), 0, 0);\n'
    '                col.addView(nt);\n'
    '            }\n')

# 7) menu: note + fingerprint
rep('        if (!a.isBackup()) c.addView(dlgMenuItem("重命名", "只改账号库里显示的名字", false, new View.OnClickListener() {',
    '        c.addView(dlgMenuItem("改备注", "给自己看的说明，比如「日服小号」", false, new View.OnClickListener() {\n'
    '            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); doEditNote(); }\n'
    '        }));\n'
    '        c.addView(dlgMenuItem("复制指纹", "复制 " + a.fpShort() + "，发给别人核对用", false, new View.OnClickListener() {\n'
    '            public void onClick(View v) {\n'
    '                if (h[0] != null) h[0].dismiss();\n'
    '                try {\n'
    '                    android.content.ClipboardManager cm = (android.content.ClipboardManager) getSystemService(CLIPBOARD_SERVICE);\n'
    '                    cm.setPrimaryClip(android.content.ClipData.newPlainText("fingerprint", a.fpShort()));\n'
    '                    toast("指纹已复制：" + a.fpShort());\n'
    '                } catch (Throwable t) { toast("复制失败"); }\n'
    '            }\n'
    '        }));\n'
    '        if (!a.isBackup()) c.addView(dlgMenuItem("重命名", "只改账号库里显示的名字", false, new View.OnClickListener() {')

# 8) new methods: insert before askNameThenSave
anchor = '    private void askNameThenSave(final String key, final String source) {'
new_methods = '''    /** 任务页：把剪贴板里的 key（或整段 xml）存进账号库。 */
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
                    + (text.length() > 120 ? "（可能是网页或说明文字）" : "") + "。\\n\\n请只复制 AuthKey 那一行，再点一次。");
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
            rowHomeFp.setTextColor(curFp != null ? Color.parseColor("#2F6BFF") : Color.parseColor("#8A93A0"));
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

'''
rep(anchor, new_methods + anchor)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched bytes", len(orig), "->", len(s))