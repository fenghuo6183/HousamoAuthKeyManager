# -*- coding: utf-8 -*-
import io, re, sys
P = "D:/123/4/android/src/com/housamo/authkey/MainActivity.java"
src = io.open(P, encoding="utf-8").read()
lines = src.split("\n")

def swap(start_pat, body, occ=0):
    """body: list of source lines without base indent"""
    idxs = [i for i, l in enumerate(lines) if start_pat in l]
    if len(idxs) <= occ:
        raise SystemExit("not found: " + start_pat)
    i = idxs[occ]
    j = None
    for k in range(i, len(lines)):
        if lines[k].strip() == ".show();":
            j = k
            break
    if j is None:
        raise SystemExit("no .show(); after " + start_pat)
    indent = re.match(r"[ ]*", lines[i]).group(0)
    new = [(indent + b) if b.strip() else "" for b in body]
    lines[i:j + 1] = new
    return i

HELPERS = [
    "",
    "    private LinearLayout dlgBtnRow() {",
    "        LinearLayout row = new LinearLayout(this);",
    "        row.setOrientation(LinearLayout.HORIZONTAL);",
    "        row.setPadding(0, dp(6), 0, 0);",
    "        return row;",
    "    }",
    "",
    "    private void dlgAddGhost(LinearLayout row, String text, View.OnClickListener click, boolean blue) {",
    "        row.addView(dlgGhost(text, click, blue), new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1.0f));",
    "    }",
    "",
    "    private EditText dlgInput(String def) {",
    "        EditText et = new EditText(this);",
    "        et.setText(def);",
    "        et.setSingleLine(true);",
    "        et.setInputType(InputType.TYPE_CLASS_TEXT);",
    "        et.setTextSize(14);",
    "        et.setTextColor(Color.parseColor(\"#101418\"));",
    "        et.setPadding(dp(12), dp(10), dp(12), dp(10));",
    "        et.setBackground(roundRect(Color.parseColor(\"#F5F7FB\"), 12, Color.parseColor(\"#E7EBF2\"), 1));",
    "        et.setSelection(et.getText().length());",
    "        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);",
    "        p.topMargin = dp(14);",
    "        et.setLayoutParams(p);",
    "        return et;",
    "    }",
    "",
    "    private View dlgMenuItem(String title, String desc, boolean danger, View.OnClickListener click) {",
    "        LinearLayout box = new LinearLayout(this);",
    "        box.setOrientation(LinearLayout.VERTICAL);",
    "        box.setBackground(roundRect(Color.parseColor(\"#F7F8FB\"), 14, 0, 0));",
    "        box.setPadding(dp(14), dp(12), dp(14), dp(12));",
    "        box.setClickable(true);",
    "        box.setOnClickListener(click);",
    "        TextView t = new TextView(this);",
    "        t.setText(title);",
    "        t.setTextSize(14);",
    "        t.setTextColor(Color.parseColor(danger ? \"#E5484D\" : \"#101418\"));",
    "        box.addView(t);",
    "        if (desc != null && desc.length() > 0) {",
    "            TextView d = new TextView(this);",
    "            d.setText(desc);",
    "            d.setTextSize(11.5f);",
    "            d.setTextColor(Color.parseColor(\"#8A93A0\"));",
    "            d.setPadding(0, dp(3), 0, 0);",
    "            box.addView(d);",
    "        }",
    "        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);",
    "        p.topMargin = dp(10);",
    "        box.setLayoutParams(p);",
    "        return box;",
    "    }",
    "",
    "    private void startTreePick() {",
    "        try {",
    "            Intent i = new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);",
    "            i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION | Intent.FLAG_GRANT_WRITE_URI_PERMISSION",
    "                    | Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);",
    "            startActivityForResult(i, REQ_TREE_COPY);",
    "        } catch (Throwable t) {",
    "            toast(\"无法打开文件夹选择器\");",
    "        }",
    "    }",
    "",
]

# 0) helpers right after showCard()
hi = [i for i, l in enumerate(lines) if l.strip() == "return d;"]
if not hi:
    raise SystemExit("showCard end not found")
# showCard ends with return d; then closing brace
h = hi[0] + 2
lines[h:h] = HELPERS

# 1) 清空账号库
swap('''.setTitle("清空账号库")''', [
    'LinearLayout c = dlgCard();',
    'dlgTitle(c, "清空账号库");',
    'dlgSub(c, "会删除本机保存的所有账号记录。各账号导出到 Download 的 AuthKey.txt 不会删。");',
    'final AlertDialog[] h = new AlertDialog[1];',
    'c.addView(dlgPrimary("清空", new View.OnClickListener() {',
    '    public void onClick(View v) {',
    '        accounts.clear();',
    '        saveVault();',
    '        refreshList();',
    '        log("[库] 已清空账号库");',
    '        if (h[0] != null) h[0].dismiss();',
    '    }',
    '}));',
    'LinearLayout row = dlgBtnRow();',
    'dlgAddGhost(row, "取消", new View.OnClickListener() {',
    '    public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }',
    '}, false);',
    'c.addView(row);',
    'h[0] = showCard(c);',
])

# 2) askNameThenSave
swap('''.setTitle("给这个账号取个名字")''', [
    'LinearLayout c = dlgCard();',
    'dlgTitle(c, "给这个账号取个名字");',
    'dlgSub(c, "会同时导出到 手机存储/" + Environment.DIRECTORY_DOWNLOADS + "/东放Key/" + game.exportSub() + "/<名字>/AuthKey.txt");',
    'final EditText et = dlgInput(defName);',
    'c.addView(et);',
    'final AlertDialog[] h = new AlertDialog[1];',
    'c.addView(dlgPrimary("保存", new View.OnClickListener() {',
    '    public void onClick(View v) {',
    '        String n = et.getText().toString().trim();',
    '        if (h[0] != null) h[0].dismiss();',
    '        addAccount(n.length() > 0 ? n : defName, key, source);',
    '    }',
    '}));',
    'LinearLayout row = dlgBtnRow();',
    'dlgAddGhost(row, "用默认名", new View.OnClickListener() {',
    '    public void onClick(View v) {',
    '        if (h[0] != null) h[0].dismiss();',
    '        addAccount(defName, key, source);',
    '    }',
    '}, false);',
    'c.addView(row);',
    'h[0] = showCard(c);',
])

# 3) doRename
swap('''.setTitle("重命名账号")''', [
    'LinearLayout c = dlgCard();',
    'dlgTitle(c, "重命名");',
    'dlgSub(c, "只改本机账号库里显示的名字，导出到 Download 的文件名不变。");',
    'final EditText et = dlgInput(a.name);',
    'et.selectAll();',
    'c.addView(et);',
    'final AlertDialog[] h = new AlertDialog[1];',
    'c.addView(dlgPrimary("保存", new View.OnClickListener() {',
    '    public void onClick(View v) {',
    '        String n = et.getText().toString().trim();',
    '        if (n.length() > 0) {',
    '            a.name = n;',
    '            saveVault();',
    '            refreshList();',
    '            log("[改名] 已改名为 " + n);',
    '        }',
    '        if (h[0] != null) h[0].dismiss();',
    '    }',
    '}));',
    'LinearLayout row = dlgBtnRow();',
    'dlgAddGhost(row, "取消", new View.OnClickListener() {',
    '    public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }',
    '}, false);',
    'c.addView(row);',
    'h[0] = showCard(c);',
])

# 4) doDelete
swap('''.setTitle(a.isBackup() ? "删除这条备份" : "删除账号")''', [
    'LinearLayout c = dlgCard();',
    'dlgTitle(c, a.isBackup() ? "删除这条备份" : "删除账号");',
    'dlgSub(c, "确定删除「" + a.name + "」？" + (a.isBackup() ? "已导出的 AuthKey.txt 不会删。" : "这条记录会从本机账号库消失，导出过的文件仍在原处。"));',
    'final AlertDialog[] h = new AlertDialog[1];',
    'Button del = dlgPrimary("删除", new View.OnClickListener() {',
    '    public void onClick(View v) {',
    '        accounts.remove(a);',
    '        saveVault();',
    '        refreshList();',
    '        log("[删除] 已删除 " + a.name);',
    '        if (h[0] != null) h[0].dismiss();',
    '    }',
    '});',
    'del.setBackground(roundRect(Color.parseColor("#E5484D"), 12, 0, 0));',
    'c.addView(del);',
    'LinearLayout row = dlgBtnRow();',
    'dlgAddGhost(row, "取消", new View.OnClickListener() {',
    '    public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }',
    '}, false);',
    'c.addView(row);',
    'h[0] = showCard(c);',
])

# 5) showAccMenu
swap('''.setItems(items.toArray(new String[0])''', [
    'LinearLayout c = dlgCard();',
    'dlgTitle(c, a.isBackup() ? a.name.replace("导入前备份", "备份") : a.name);',
    'dlgSub(c, "指纹 " + a.fpShort() + (a.isBackup() ? " · 自动备份" : " · 账号"));',
    'final AlertDialog[] h = new AlertDialog[1];',
    'c.addView(dlgMenuItem("导入到游戏", "写进游戏，覆盖当前登录的 key", false, new View.OnClickListener() {',
    '    public void onClick(View v) { if (h[0] != null) h[0].dismiss(); doImport(); }',
    '}));',
    'if (!a.isBackup()) c.addView(dlgMenuItem("重命名", "只改账号库里显示的名字", false, new View.OnClickListener() {',
    '    public void onClick(View v) { if (h[0] != null) h[0].dismiss(); doRename(); }',
    '}));',
    'c.addView(dlgMenuItem("删除", a.isBackup() ? "只删这条备份，导出文件不动" : "从账号库移除，导出文件不动", true, new View.OnClickListener() {',
    '    public void onClick(View v) { if (h[0] != null) h[0].dismiss(); doDelete(); }',
    '}));',
    'LinearLayout row = dlgBtnRow();',
    'dlgAddGhost(row, "取消", new View.OnClickListener() {',
    '    public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }',
    '}, true);',
    'c.addView(row);',
    'h[0] = showCard(c);',
])

# 6) startCopyMove
swap('''.setItems(new String[]{"复制一份（原来的保留）", "移动过去（删掉原来导出的那份）"}''', [
    'LinearLayout c = dlgCard();',
    'dlgTitle(c, "放到其他文件夹");',
    'dlgSub(c, "会打开系统的文件夹选择器，选一个目标目录，写进去之后可以随时再用文件管理器挪走。");',
    'final AlertDialog[] h = new AlertDialog[1];',
    'c.addView(dlgMenuItem("复制一份", "原来的导出文件保留，目标文件夹里多一份", false, new View.OnClickListener() {',
    '    public void onClick(View v) {',
    '        copyTarget = a;',
    '        copyMove = false;',
    '        if (h[0] != null) h[0].dismiss();',
    '        startTreePick();',
    '    }',
    '}));',
    'c.addView(dlgMenuItem("移动过去", "写成功后删掉原来导出的那一份", false, new View.OnClickListener() {',
    '    public void onClick(View v) {',
    '        copyTarget = a;',
    '        copyMove = true;',
    '        if (h[0] != null) h[0].dismiss();',
    '        startTreePick();',
    '    }',
    '}));',
    'LinearLayout row = dlgBtnRow();',
    'dlgAddGhost(row, "取消", new View.OnClickListener() {',
    '    public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }',
    '}, true);',
    'c.addView(row);',
    'h[0] = showCard(c);',
])

# 7) doImport confirm
swap('''.setTitle("导入到游戏？")''', [
    'LinearLayout c = dlgCard();',
    'dlgTitle(c, "导入到游戏？");',
    'dlgSub(c, msg);',
    'final AlertDialog[] h = new AlertDialog[1];',
    'c.addView(dlgPrimary("导入", new View.OnClickListener() {',
    '    public void onClick(View v) {',
    '        if (h[0] != null) h[0].dismiss();',
    '        doImportNow(a);',
    '    }',
    '}));',
    'LinearLayout row = dlgBtnRow();',
    'dlgAddGhost(row, "取消", new View.OnClickListener() {',
    '    public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }',
    '}, false);',
    'c.addView(row);',
    'h[0] = showCard(c);',
])

# 8) 导入完成
swap('''.setTitle("导入完成")''', [
    'LinearLayout c = dlgCard();',
    'dlgTitle(c, "导入完成");',
    'dlgSub(c, "已写入并校验通过。点「打开游戏」，进去就是「" + a.name + "」这个账号。");',
    'final AlertDialog[] h = new AlertDialog[1];',
    'c.addView(dlgPrimary("打开游戏", new View.OnClickListener() {',
    '    public void onClick(View v) {',
    '        if (h[0] != null) h[0].dismiss();',
    '        launchGame();',
    '    }',
    '}));',
    'LinearLayout row = dlgBtnRow();',
    'dlgAddGhost(row, "稍后", new View.OnClickListener() {',
    '    public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }',
    '}, false);',
    'c.addView(row);',
    'h[0] = showCard(c);',
])

out = "\n".join(lines)
io.open(P, "w", encoding="utf-8", newline="\n").write(out)
print("done", len(out))
