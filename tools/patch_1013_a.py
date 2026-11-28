# -*- coding: utf-8 -*-
import io, sys

P = "D:/123/4/android/src/com/housamo/authkey/MainActivity.java"
src = io.open(P, encoding="utf-8").read()
orig_len = len(src)

def rep(old, new, why):
    global src
    n = src.count(old)
    assert n == 1, "anchor count=%d for %s" % (n, why)
    src = src.replace(old, new, 1)

# ---------- 1. 游戏配置 ----------
rep('''    static final String PKG = "jp.co.lifewonders.housamo";
    static final String EXT_DIR = "/sdcard/Android/data/" + PKG + "/files/Data";
    static final String EXT_KEY = EXT_DIR + "/AuthKey";
    static final String PREFS1 = "/data/data/" + PKG + "/shared_prefs/" + PKG + ".v2.playerprefs.xml";
    static final String PREFS2 = "/data/user/0/" + PKG + "/shared_prefs/" + PKG + ".v2.playerprefs.xml";''',
'''    /** 一个受支持的游戏：包名 + key 文件在外部数据目录里的位置。 */
    static class Game {
        final String id, label, pkg, sub, file;

        Game(String id, String label, String pkg, String sub, String file) {
            this.id = id;
            this.label = label;
            this.pkg = pkg;
            this.sub = sub;
            this.file = file;
        }

        String extDir() {
            return "/sdcard/Android/data/" + pkg + "/" + sub;
        }

        String extKey() {
            return extDir() + "/" + file;
        }

        /** 导出 / 备份目录里这个游戏用的子文件夹（东放沿用老路径，不加子目录）。 */
        String exportSub() {
            return "housamo".equals(id) ? "" : label;
        }
    }

    static final Game GAME_HOUSAMO = new Game("housamo", "东京放课后", "jp.co.lifewonders.housamo", "files/Data", "AuthKey");
    static final Game GAME_LIVEHERO = new Game("liveahero", "LiveAHero", "jp.co.lifewonders.liveahero", "files/datas", "userKey");
    static final Game[] GAMES = new Game[]{GAME_HOUSAMO, GAME_LIVEHERO};

    /** 当前游戏；切换时下面这组路径会被重写，其余代码不用动。 */
    static Game game = GAME_HOUSAMO;
    static String PKG = GAME_HOUSAMO.pkg;
    static String EXT_DIR = GAME_HOUSAMO.extDir();
    static String EXT_KEY = GAME_HOUSAMO.extKey();
    static String PREFS1 = "/data/data/" + PKG + "/shared_prefs/" + PKG + ".v2.playerprefs.xml";
    static String PREFS2 = "/data/user/0/" + PKG + "/shared_prefs/" + PKG + ".v2.playerprefs.xml";

    static Game gameById(String id) {
        for (Game g : GAMES) if (g.id.equals(id)) return g;
        return GAME_HOUSAMO;
    }''', "game model")

# ---------- 2. Account 增加 game 字段 ----------
rep('''        String folder = "";
        String kind = "account";''',
'''        String folder = "";
        String kind = "account";
        /** 属于哪个游戏（housamo / liveahero）；空 = 老数据，算作东京放课后。 */
        String game = "housamo";''', "account field")

rep('''            o.put("kind", kind);
            return o;''',
'''            o.put("kind", kind);
            o.put("game", game);
            return o;''', "account toJson")

rep('''            a.kind = o.optString("kind", "");''',
'''            a.kind = o.optString("kind", "");
            a.game = o.optString("game", "housamo");
            if (a.game == null || a.game.length() == 0) a.game = "housamo";''', "account fromJson")

# ---------- 3. 字段与 onCreate ----------
rep('''    private String curFp = null;''',
'''    private String curFp = null;
    /** 游戏里当前 key 的原文（启动核对要用）。 */
    private String curKey = null;
    /** 用户在核对卡片上点过「不用管」的那个指纹，不再重复打扰。 */
    private String bannerDismissedFp = null;
    private LinearLayout bannerBox = null;
    private final java.util.List<Button> gameButtons = new java.util.ArrayList<Button>();''', "banner fields")

rep('''        super.onCreate(savedInstanceState);
        setContentView(buildUi());''',
'''        super.onCreate(savedInstanceState);
        applyGame(gameById(getPreferences(MODE_PRIVATE).getString("gameId", "housamo")));
        setContentView(buildUi());''', "onCreate applyGame")

rep('''    // ---------- 生命周期 ----------''',
'''    /** 切换当前游戏：把静态路径全部指到这个游戏上。 */
    private void applyGame(Game g) {
        if (g == null) g = GAME_HOUSAMO;
        game = g;
        PKG = g.pkg;
        EXT_DIR = g.extDir();
        EXT_KEY = g.extKey();
        PREFS1 = "/data/data/" + g.pkg + "/shared_prefs/" + g.pkg + ".v2.playerprefs.xml";
        PREFS2 = "/data/user/0/" + g.pkg + "/shared_prefs/" + g.pkg + ".v2.playerprefs.xml";
    }

    // ---------- 生命周期 ----------''', "applyGame")

# ---------- 4. updateState ----------
rep('''        if (rowGameVal != null) {
            rowGameVal.setText(gameInstalled ? "已检测到" : "未检测到");
            rowGameVal.setTextColor(gameInstalled ? okColor : noColor);
        }''',
'''        if (rowGameVal != null) {
            rowGameVal.setText(game.label + (gameInstalled ? " · 已安装" : " · 未安装"));
            rowGameVal.setTextColor(gameInstalled ? okColor : noColor);
        }''', "updateState game row")

rep('''        refreshAccountsView();
        if (rowSelVal != null) {''',
'''        refreshAccountsView();
        styleGameBtns();
        if (rowSelVal != null) {''', "updateState style btns")

# ---------- 5. 按游戏过滤 ----------
rep('''    private int countAccounts() {
        int n = 0;
        for (Account a : accounts) if (!a.isBackup()) n++;
        return n;
    }''',
'''    /** 这条记录是不是属于当前游戏。 */
    private boolean inGame(Account a) {
        if (a == null) return false;
        String g = (a.game == null || a.game.length() == 0) ? "housamo" : a.game;
        return g.equals(game.id);
    }

    private int countAccounts() {
        int n = 0;
        for (Account a : accounts) if (!a.isBackup() && inGame(a)) n++;
        return n;
    }''', "inGame")

rep('''    private int countBackups() {
        int n = 0;
        for (Account a : accounts) if (a.isBackup()) n++;
        return n;
    }''',
'''    private int countBackups() {
        int n = 0;
        for (Account a : accounts) if (a.isBackup() && inGame(a)) n++;
        return n;
    }''', "countBackups")

rep('''        for (int i = accounts.size() - 1; i >= 0; i--) {
            Account a = accounts.get(i);
            if (a.isBackup() == (accTab == 1)) accView.add(a);
        }''',
'''        for (int i = accounts.size() - 1; i >= 0; i--) {
            Account a = accounts.get(i);
            if (!inGame(a)) continue;
            if (a.isBackup() == (accTab == 1)) accView.add(a);
        }''', "accView filter")

rep('''        for (Account b : accounts) {
            if (b.isBackup() && !isExportEntry(b) && b.key != null && b.key.trim().equals(k)) return b;
        }''',
'''        for (Account b : accounts) {
            if (b.isBackup() && inGame(b) && !isExportEntry(b) && b.key != null && b.key.trim().equals(k)) return b;
        }''', "findBackupOfKey")

rep('''        for (Account b : accounts) {
            if (b != a && a.key.equals(b.key)) return true;
        }''',
'''        for (Account b : accounts) {
            if (b != a && inGame(b) && a.key.equals(b.key)) return true;
        }''', "isDup")

rep('''            for (Account a : accounts) {
                if (a.key != null && a.key.trim().equals(f.key)) {''',
'''            for (Account a : accounts) {
                if (inGame(a) && a.key != null && a.key.trim().equals(f.key)) {''', "syncFromExportFolder")

io.open(P, "w", encoding="utf-8").write(src)
print("part1 ok, len", orig_len, "->", len(src))
