# -*- coding: utf-8 -*-
import io, re
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
orig = s

# 1) all literal colors go through the theme mapper
s2, n = re.subn(r'Color\.parseColor\(', 'c(', s)
print("replaced colors", n)

# 2) surface whites -> themed (keep text whites)
def rep(old, new, cnt=1):
    global s2
    assert s2.count(old) == cnt, ("anchor %d: %r" % (s2.count(old), old[:80]))
    s2 = s2.replace(old, new, cnt)

rep('nav.setBackgroundColor(Color.WHITE);', 'nav.setBackgroundColor(c("#FFFFFF"));')
rep('bClear.setBackground(roundRect(Color.WHITE, 10, c("#F3B4B6"), 1));', 'bClear.setBackground(roundRect(c("#FFFFFF"), 10, c("#F3B4B6"), 1));')
rep('box.setBackground(roundRect(on ? c("#F2F6FF") : Color.WHITE,', 'box.setBackground(roundRect(on ? c("#F2F6FF") : c("#FFFFFF"),')
rep('c.setBackground(roundRect(Color.WHITE, 16, c("#EBEEF3"), 1));', 'c.setBackground(roundRect(c("#FFFFFF"), 16, c("#EBEEF3"), 1));')
rep('b.setBackground(roundRect(Color.WHITE, 10, c("#DCE1E8"), 1));', 'b.setBackground(roundRect(c("#FFFFFF"), 10, c("#DCE1E8"), 1));')
rep('c.setBackground(roundRect(Color.WHITE, 20, 0, 0));', 'c.setBackground(roundRect(c("#FFFFFF"), 20, 0, 0));')

# 3) theme helpers + night pref, insert before "private LinearLayout page()"
helpers = '''    // ---------- 主题（浅色 / 深色） ----------

    private boolean night() {
        return getPreferences(MODE_PRIVATE).getBoolean("night", false);
    }

    /** 所有颜色都从这里过一道，深色模式下自动换成暗色。 */
    private int c(String hex) {
        if (!night()) return Color.parseColor(hex);
        String h = hex.toUpperCase(Locale.US);
        if ("#FFFFFF".equals(h)) return Color.parseColor("#171B21");
        if ("#F2F3F6".equals(h)) return Color.parseColor("#0E1116");
        if ("#101418".equals(h)) return Color.parseColor("#E7ECF3");
        if ("#2B3442".equals(h)) return Color.parseColor("#D7DEE8");
        if ("#3B4252".equals(h)) return Color.parseColor("#CFD6E1");
        if ("#5B6470".equals(h) || "#5B6572".equals(h)) return Color.parseColor("#AAB4C2");
        if ("#8A93A0".equals(h) || "#9AA3B0".equals(h)) return Color.parseColor("#8B96A6");
        if ("#EBEEF3".equals(h) || "#EBEFF5".equals(h) || "#EFF1F5".equals(h)) return Color.parseColor("#2A3038");
        if ("#E6E9EF".equals(h) || "#DCE1E8".equals(h) || "#E7EBF2".equals(h) || "#E6EAF1".equals(h)) return Color.parseColor("#2A3038");
        if ("#F2F4F8".equals(h) || "#F3F5F9".equals(h) || "#F5F7FB".equals(h) || "#F7F8FB".equals(h)) return Color.parseColor("#1E242C");
        if ("#F2F6FF".equals(h) || "#EAF0FF".equals(h)) return Color.parseColor("#1B2536");
        if ("#E8F7EF".equals(h)) return Color.parseColor("#16301F");
        if ("#FBF3DA".equals(h)) return Color.parseColor("#2E2716");
        if ("#8A6D1F".equals(h) || "#A3741A".equals(h)) return Color.parseColor("#E3BC63");
        if ("#19A974".equals(h)) return Color.parseColor("#4ADE80");
        if ("#F3B4B6".equals(h)) return Color.parseColor("#7A3B3E");
        int v = Color.parseColor(hex);
        int lum = (Color.red(v) * 299 + Color.green(v) * 587 + Color.blue(v) * 114) / 1000;
        if (lum >= 225) return Color.parseColor("#1A2028");
        if (lum >= 195) return Color.parseColor("#232A34");
        if (lum <= 95) return Color.parseColor("#DCE3EC");
        return v;
    }

    private void applyTheme() {
        boolean n = night();
        try {
            getWindow().setStatusBarColor(c("#F2F3F6"));
            getWindow().setNavigationBarColor(n ? c("#0E1116") : c("#FFFFFF"));
            if (Build.VERSION.SDK_INT >= 23 && !n) {
                getWindow().getDecorView().setSystemUiVisibility(android.view.View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR);
            } else if (Build.VERSION.SDK_INT >= 23) {
                getWindow().getDecorView().setSystemUiVisibility(0);
            }
        } catch (Throwable ignored) {
        }
    }

    private void toggleNight() {
        getPreferences(MODE_PRIVATE).edit().putBoolean("night", !night()).apply();
        recreate();
    }

'''
rep('''    private LinearLayout page() {''', helpers + '    private LinearLayout page() {')

# 4) settings row for dark mode + apply theme in buildUi
rep('''        p.addView(perm, cardParams(0));

        LinearLayout exp = card();''',
    '''        p.addView(perm, cardParams(0));

        LinearLayout look = card();
        look.addView(caption("外观"));
        rowNightVal = value(0, night() ? "深色" : "浅色");
        look.addView(rowWith(rowNightVal, "深色模式", new View.OnClickListener() {
            public void onClick(View v) { toggleNight(); }
        }));
        TextView lh = new TextView(this);
        lh.setText("深色模式只是换个配色，读写行为完全一样。");
        lh.setTextSize(11);
        lh.setTextColor(c("#9AA3B0"));
        lh.setPadding(dp(2), dp(10), dp(2), dp(2));
        look.addView(lh);
        p.addView(look, cardParams(0));

        LinearLayout exp = card();''')

rep('    private TextView rowKeepVal;', '    private TextView rowKeepVal, rowNightVal, rowLockVal, rowShotVal;')

rep('''        root.setBackgroundColor(c("#F2F3F6"));''',
    '''        root.setBackgroundColor(c("#F2F3F6"));
        applyTheme();''')

io.open(P, "w", encoding="utf-8", newline="\n").write(s2)
print("patched", len(orig), "->", len(s2))