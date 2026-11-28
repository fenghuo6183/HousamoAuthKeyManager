# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
orig = s
def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, ("anchor %d: %r" % (s.count(old), old[:80]))
    s = s.replace(old, new, cnt)

# const
rep('    private static final int REQ_TREE_ZIP = 0x75;',
    '    private static final int REQ_TREE_ZIP = 0x75;\n    private static final int REQ_QR_IMG = 0x76;')

# task card
rep('''        p.addView(taskCard("打包导出全部 key",''',
    '''        p.addView(taskCard("从二维码图片导入 key", "别人把 key 做成二维码发给你时，从相册或文件里选那张图，自动解出 key 存进账号库。", new View.OnClickListener() {
            public void onClick(View v) { pickQrImage(); }
        }), cardParams(0));

        p.addView(taskCard("打包导出全部 key",''')

# menu item for generating QR
rep('''        c.addView(dlgMenuItem("复制指纹", "复制 " + a.fpShort() + "，发给别人核对用", false, new View.OnClickListener() {''',
    '''        c.addView(dlgMenuItem("生成二维码", "把这个 key 做成二维码图片，方便当面发给另一台手机", false, new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); makeQr(a); }
        }));
        c.addView(dlgMenuItem("复制指纹", "复制 " + a.fpShort() + "，发给别人核对用", false, new View.OnClickListener() {''')

# methods
anchor = '    // ---------- 导入历史 / 备份保留 / 撤销 / 打包导出 ----------'
methods = '''    // ---------- 二维码 ----------

    private void pickQrImage() {
        try {
            Intent i = new Intent(Intent.ACTION_GET_CONTENT);
            i.setType("image/*");
            i.addCategory(Intent.CATEGORY_OPENABLE);
            startActivityForResult(Intent.createChooser(i, "选一张二维码图片"), REQ_QR_IMG);
        } catch (Throwable t) {
            toast("打不开图片选择器");
        }
    }

    private void decodeQrUri(final android.net.Uri uri) {
        log("[二维码] 正在识别图片…");
        pool.execute(new Runnable() {
            public void run() {
                String text = null;
                String err = null;
                try {
                    android.graphics.BitmapFactory.Options o = new android.graphics.BitmapFactory.Options();
                    o.inJustDecodeBounds = true;
                    android.graphics.BitmapFactory.decodeStream(getContentResolver().openInputStream(uri), null, o);
                    int scale = 1;
                    while (o.outWidth / scale > 1400 || o.outHeight / scale > 1400) scale *= 2;
                    android.graphics.BitmapFactory.Options o2 = new android.graphics.BitmapFactory.Options();
                    o2.inSampleSize = scale;
                    android.graphics.Bitmap bm = android.graphics.BitmapFactory.decodeStream(
                            getContentResolver().openInputStream(uri), null, o2);
                    if (bm == null) throw new Exception("图片读不出来");
                    int w = bm.getWidth(), h = bm.getHeight();
                    int[] px = new int[w * h];
                    bm.getPixels(px, 0, w, 0, 0, w, h);
                    com.google.zxing.RGBLuminanceSource src = new com.google.zxing.RGBLuminanceSource(w, h, px);
                    com.google.zxing.BinaryBitmap bb = new com.google.zxing.BinaryBitmap(
                            new com.google.zxing.common.HybridBinarizer(src));
                    com.google.zxing.Result rr = new com.google.zxing.MultiFormatReader().decode(bb);
                    text = rr.getText();
                } catch (com.google.zxing.NotFoundException nf) {
                    err = "图片里没有二维码，或者二维码太糊";
                } catch (Throwable t) {
                    err = "识别失败：" + t;
                }
                final String tt = text;
                final String ee = err;
                runOnUiThread(new Runnable() {
                    public void run() {
                        if (tt == null) {
                            log("[二维码] " + ee);
                            toast(ee == null ? "没识别出内容" : ee);
                            return;
                        }
                        String k = tt.trim();
                        if (k.contains("<string") && k.contains("AuthKey")) {
                            String x = extractFromPrefs(k);
                            if (x != null && x.trim().length() > 0) k = x.trim();
                        }
                        if (!isKeyLike(k)) {
                            log("[二维码] 解出来的内容不像 key（" + k.length() + " 字符）");
                            toast("二维码里不是 key");
                            return;
                        }
                        log("[二维码] 已识别出 key，指纹 " + hash(k).substring(0, 16));
                        if (libraryHasKey(k)) toast("这个 key 账号库里已经有了");
                        askNameThenSave(k, "二维码");
                    }
                });
            }
        });
    }

    private void makeQr(final Account a) {
        pool.execute(new Runnable() {
            public void run() {
                File out = null;
                try {
                    int S = 660;
                    java.util.Hashtable<com.google.zxing.EncodeHintType, Object> hints =
                            new java.util.Hashtable<com.google.zxing.EncodeHintType, Object>();
                    hints.put(com.google.zxing.EncodeHintType.CHARACTER_SET, "UTF-8");
                    hints.put(com.google.zxing.EncodeHintType.MARGIN, 2);
                    com.google.zxing.common.BitMatrix m = new com.google.zxing.qrcode.QRCodeWriter()
                            .encode(a.key, com.google.zxing.BarcodeFormat.QR_CODE, S, S, hints);
                    int[] px = new int[S * S];
                    for (int y = 0; y < S; y++) {
                        for (int x = 0; x < S; x++) {
                            px[y * S + x] = m.get(x, y) ? 0xFF101418 : 0xFFFFFFFF;
                        }
                    }
                    android.graphics.Bitmap bm = android.graphics.Bitmap.createBitmap(S, S, android.graphics.Bitmap.Config.ARGB_8888);
                    bm.setPixels(px, 0, S, 0, 0, S, S);
                    File dir = new File(getCacheDir(), "qr");
                    if (!dir.exists()) dir.mkdirs();
                    out = new File(dir, safeName(a.name) + "-" + a.fpShort() + ".png");
                    java.io.FileOutputStream fo = new java.io.FileOutputStream(out);
                    bm.compress(android.graphics.Bitmap.CompressFormat.PNG, 100, fo);
                    fo.close();
                } catch (Throwable t) {
                    log("[二维码] 生成失败：" + t);
                    out = null;
                }
                final File f = out;
                runOnUiThread(new Runnable() {
                    public void run() {
                        if (f == null) { toast("生成二维码失败"); return; }
                        log("[二维码] 已生成 " + f.getName());
                        LinearLayout c = dlgCard();
                        dlgTitle(c, a.name);
                        dlgSub(c, "扫这个二维码就能拿到 key。发给别人等于把账号交给对方，注意场合。");
                        android.widget.ImageView iv = new android.widget.ImageView(MainActivity.this);
                        android.graphics.Bitmap bm2 = android.graphics.BitmapFactory.decodeFile(f.getAbsolutePath());
                        iv.setImageBitmap(bm2);
                        iv.setAdjustViewBounds(true);
                        iv.setBackground(roundRect(c("#FFFFFF"), 12, 0, 0));
                        iv.setPadding(dp(8), dp(8), dp(8), dp(8));
                        LinearLayout.LayoutParams ilp = new LinearLayout.LayoutParams(
                                ViewGroup.LayoutParams.MATCH_PARENT, dp(230));
                        ilp.setMargins(0, dp(8), 0, 0);
                        c.addView(iv, ilp);
                        final AlertDialog[] h = new AlertDialog[1];
                        c.addView(dlgPrimary("分享这张二维码", new View.OnClickListener() {
                            public void onClick(View v) {
                                if (h[0] != null) h[0].dismiss();
                                try {
                                    android.net.Uri u = ApkProvider.uriForQr(f);
                                    Intent sh = new Intent(Intent.ACTION_SEND);
                                    sh.setType("image/png");
                                    sh.putExtra(Intent.EXTRA_STREAM, u);
                                    sh.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                                    startActivity(Intent.createChooser(sh, "分享二维码"));
                                } catch (Throwable t) {
                                    toast("分享失败：" + t);
                                }
                            }
                        }));
                        LinearLayout row = dlgBtnRow();
                        dlgAddGhost(row, "关闭", new View.OnClickListener() {
                            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
                        }, false);
                        c.addView(row);
                        h[0] = showCard(c);
                    }
                });
            }
        });
    }

'''
rep(anchor, methods + anchor)

# onActivityResult branch
rep('''        android.net.Uri uri = data.getData();
        if (req != REQ_TREE''',
    '''        android.net.Uri uri = data.getData();
        if (req == REQ_QR_IMG) {
            decodeQrUri(uri);
            return;
        }
        if (req != REQ_TREE''')

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched", len(orig), "->", len(s))