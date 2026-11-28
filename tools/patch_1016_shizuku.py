# -*- coding: utf-8 -*-
import io, re
P = "D:/123/4/android/src/com/housamo/authkey/MainActivity.java"
lines = io.open(P, encoding="utf-8").read().split("\n")

def swap(start_pat, body):
    idxs = [i for i, l in enumerate(lines) if start_pat in l]
    if not idxs:
        raise SystemExit("not found: " + start_pat)
    i = idxs[0]
    j = None
    for k in range(i, len(lines)):
        if lines[k].strip() == ".show();":
            j = k
            break
    if j is None:
        raise SystemExit("no show")
    indent = re.match(r"[ ]*", lines[i]).group(0)
    lines[i - 1:j + 1] = [(indent + b) if b.strip() else "" for b in body]

swap('.setTitle("未安装 Shizuku")', [
    'LinearLayout c = dlgCard();',
    'dlgTitle(c, "还没装 Shizuku");',
    'dlgSub(c, "Shizuku 能把 adb 权限借给本应用，让 Android 11+ 不用 root 也能读写游戏目录。装好后打开它，按提示用「无线调试」启动，再回这里点「Shizuku 权限」授权。");',
    'final AlertDialog[] h = new AlertDialog[1];',
    'c.addView(dlgPrimary("去下载 Shizuku", new View.OnClickListener() {',
    '    public void onClick(View v) {',
    '        if (h[0] != null) h[0].dismiss();',
    '        openUrl("https://github.com/RikkaApps/Shizuku/releases/latest");',
    '    }',
    '}));',
    'LinearLayout row = dlgBtnRow();',
    'dlgAddGhost(row, "取消", new View.OnClickListener() {',
    '    public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }',
    '}, false);',
    'c.addView(row);',
    'h[0] = showCard(c);',
])

swap('.setTitle("Shizuku 未启动")', [
    'LinearLayout c = dlgCard();',
    'dlgTitle(c, "Shizuku 还没启动");',
    'dlgSub(c, "打开 Shizuku 后按它的提示启动服务（手机重启后要重新启动一次），再回这里点「刷新」或「Shizuku 权限」。");',
    'final AlertDialog[] h = new AlertDialog[1];',
    'c.addView(dlgPrimary("打开 Shizuku", new View.OnClickListener() {',
    '    public void onClick(View v) {',
    '        if (h[0] != null) h[0].dismiss();',
    '        Intent i = getPackageManager().getLaunchIntentForPackage("moe.shizuku.privileged.api");',
    '        if (i != null) startActivity(i);',
    '        else openUrl("https://github.com/RikkaApps/Shizuku/releases/latest");',
    '    }',
    '}));',
    'LinearLayout row = dlgBtnRow();',
    'dlgAddGhost(row, "取消", new View.OnClickListener() {',
    '    public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }',
    '}, false);',
    'c.addView(row);',
    'h[0] = showCard(c);',
])

io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("ok")
