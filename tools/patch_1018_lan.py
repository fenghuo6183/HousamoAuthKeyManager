# -*- coding: utf-8 -*-
import io
P = "android/src/com/housamo/authkey/MainActivity.java"
s = io.open(P, encoding="utf-8").read()
orig = s
def rep(old, new, cnt=1):
    global s
    assert s.count(old) == cnt, ("anchor %d: %r" % (s.count(old), old[:80]))
    s = s.replace(old, new, cnt)

# settings row
rep('''        bh.addView(divider());
        bh.addView(rowWith(value(0, "看每一次导入前的 key"), "导入历史", new View.OnClickListener() {''',
    '''        bh.addView(divider());
        bh.addView(rowWith(value(0, "手机和电脑同一个 WiFi"), "局域网传输", new View.OnClickListener() {
            public void onClick(View v) { showLanTransfer(); }
        }));
        bh.addView(divider());
        bh.addView(rowWith(value(0, "看每一次导入前的 key"), "导入历史", new View.OnClickListener() {''')

# methods
anchor = '    // ---------- 二维码 ----------'
methods = '''    // ---------- 局域网传输（手机开一个小网页，电脑浏览器直接下载） ----------

    private void showLanTransfer() {
        final LanServer srv;
        try {
            srv = new LanServer();
            srv.start();
        } catch (Throwable t) {
            toast("启动失败：" + t);
            return;
        }
        String ip = lanIp();
        if (ip == null) {
            toast("没连上 WiFi");
            srv.stop();
            return;
        }
        final String url = "http://" + ip + ":" + srv.port + "/?k=" + srv.code;
        LinearLayout c = dlgCard();
        dlgTitle(c, "局域网传输");
        dlgSub(c, "让手机和电脑连同一个 WiFi，在电脑浏览器里打开下面这个地址，就能看到账号列表并下载 key。\\n\\n关掉这个窗口就停止，不会一直开着。");
        TextView u = new TextView(this);
        u.setText(url);
        u.setTextSize(13);
        u.setTextColor(c("#2F6BFF"));
        u.setTypeface(android.graphics.Typeface.MONOSPACE);
        u.setTextIsSelectable(true);
        u.setPadding(dp(12), dp(12), dp(12), dp(12));
        u.setBackground(roundRect(c("#F2F4F8"), 10, 0, 0));
        c.addView(u);
        TextView tip = new TextView(this);
        tip.setText("配对码 " + srv.code + " 已经写进地址里；别人就算扫到 IP，没有这个码也打不开。");
        tip.setTextSize(11);
        tip.setTextColor(c("#9AA3B0"));
        tip.setPadding(dp(2), dp(8), dp(2), 0);
        c.addView(tip);
        final AlertDialog[] h = new AlertDialog[1];
        c.addView(dlgPrimary("复制地址", new View.OnClickListener() {
            public void onClick(View v) {
                try {
                    android.content.ClipboardManager cm = (android.content.ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
                    cm.setPrimaryClip(android.content.ClipData.newPlainText("lan", url));
                    toast("地址已复制");
                } catch (Throwable t) { toast("复制失败"); }
            }
        }));
        LinearLayout row = dlgBtnRow();
        dlgAddGhost(row, "停止", new View.OnClickListener() {
            public void onClick(View v) { if (h[0] != null) h[0].dismiss(); }
        }, false);
        c.addView(row);
        h[0] = showCard(c);
        h[0].setOnDismissListener(new android.content.DialogInterface.OnDismissListener() {
            public void onDismiss(android.content.DialogInterface d) {
                srv.stop();
                log("[局域网] 已停止");
            }
        });
        log("[局域网] 已启动 " + url);
    }

    /** 取本机 WiFi/热点的 IPv4 地址。 */
    private String lanIp() {
        try {
            java.util.Enumeration<java.net.NetworkInterface> en = java.net.NetworkInterface.getNetworkInterfaces();
            while (en.hasMoreElements()) {
                java.net.NetworkInterface ni = en.nextElement();
                if (!ni.isUp() || ni.isLoopback()) continue;
                java.util.Enumeration<java.net.InetAddress> as = ni.getInetAddresses();
                while (as.hasMoreElements()) {
                    java.net.InetAddress a = as.nextElement();
                    if (a instanceof java.net.Inet4Address && !a.isLoopbackAddress()) {
                        String ip = a.getHostAddress();
                        if (ip != null && ip.startsWith("192.168.") || ip != null && ip.startsWith("10.")
                                || ip != null && ip.startsWith("172.")) return ip;
                    }
                }
            }
        } catch (Throwable ignored) {
        }
        return null;
    }

    /** 极简 HTTP 服务：只服务一个列表页 + 每个 key 的下载。 */
    private class LanServer extends Thread {
        final java.net.ServerSocket ss;
        final int port;
        final String code;
        volatile boolean running = true;

        LanServer() throws Exception {
            java.net.ServerSocket s = null;
            int p = 8765;
            for (int i = 0; i < 20; i++) {
                try {
                    s = new java.net.ServerSocket(p + i, 8, java.net.InetAddress.getByName("0.0.0.0"));
                    p = p + i;
                    break;
                } catch (Throwable ignored) {
                }
            }
            if (s == null) throw new Exception("没有可用端口");
            ss = s;
            port = p;
            code = String.format(Locale.US, "%04d", 1000 + new java.util.Random().nextInt(9000));
            setDaemon(true);
        }

        public void stop() {
            running = false;
            try { ss.close(); } catch (Throwable ignored) {}
        }

        public void run() {
            while (running) {
                java.net.Socket sk = null;
                try {
                    sk = ss.accept();
                    handle(sk);
                } catch (Throwable ignored) {
                } finally {
                    try { if (sk != null) sk.close(); } catch (Throwable ignored) {}
                }
            }
        }

        private void handle(java.net.Socket sk) {
            try {
                sk.setSoTimeout(8000);
                java.io.BufferedReader in = new java.io.BufferedReader(
                        new java.io.InputStreamReader(sk.getInputStream(), "UTF-8"));
                String line = in.readLine();
                if (line == null) return;
                String[] parts = line.split(" ");
                if (parts.length < 2) return;
                String path = parts[1];
                java.io.OutputStream out = sk.getOutputStream();
                if (path.startsWith("/?k=" + code) || path.equals("/?k=" + code)) {
                    byte[] body = lanPage().getBytes("UTF-8");
                    head(out, "200 OK", "text/html; charset=utf-8", body.length);
                    out.write(body);
                } else if (path.startsWith("/key?i=") && path.contains("k=" + code)) {
                    int i = Integer.parseInt(path.substring(7, path.indexOf('&')));
                    java.util.List<Account> list = lanList();
                    if (i < 0 || i >= list.size()) {
                        head(out, "404 Not Found", "text/plain; charset=utf-8", 0);
                    } else {
                        Account a = list.get(i);
                        byte[] body = a.key.getBytes("UTF-8");
                        head(out, "200 OK", "application/octet-stream", body.length,
                                "attachment; filename=\\"AuthKey.txt\\"");
                        out.write(body);
                    }
                } else {
                    byte[] body = "配对码不对。请在 App 里重新打开局域网传输，用完整的地址。".getBytes("UTF-8");
                    head(out, "403 Forbidden", "text/plain; charset=utf-8", body.length);
                    out.write(body);
                }
                out.flush();
            } catch (Throwable ignored) {
            }
        }

        private void head(java.io.OutputStream out, String status, String type, int len) throws Exception {
            head(out, status, type, len, null);
        }

        private void head(java.io.OutputStream out, String status, String type, int len, String disp) throws Exception {
            StringBuilder h = new StringBuilder();
            h.append("HTTP/1.1 ").append(status).append("\\r\\n");
            h.append("Content-Type: ").append(type).append("\\r\\n");
            h.append("Content-Length: ").append(len).append("\\r\\n");
            h.append("Connection: close\\r\\n");
            if (disp != null) h.append("Content-Disposition: ").append(disp).append("\\r\\n");
            h.append("\\r\\n");
            out.write(h.toString().getBytes("UTF-8"));
        }

        private java.util.List<Account> lanList() {
            java.util.List<Account> l = new ArrayList<Account>();
            for (Account a : accounts) if (inGame(a) && !a.isBackup()) l.add(a);
            return l;
        }

        private String lanPage() {
            java.util.List<Account> l = lanList();
            StringBuilder b = new StringBuilder();
            b.append("<!doctype html><html><head><meta charset=\\"utf-8\\">");
            b.append("<meta name=\\"viewport\\" content=\\"width=device-width,initial-scale=1\\">");
            b.append("<title>东放 Key 管家 · 局域网传输</title><style>");
            b.append("body{font:15px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC',sans-serif;");
            b.append("background:#f2f3f6;color:#101418;margin:0;padding:24px}");
            b.append(".w{max-width:640px;margin:0 auto}h1{font-size:20px;margin:0 0 4px}");
            b.append(".s{color:#8a93a0;font-size:13px;margin-bottom:18px}");
            b.append(".i{background:#fff;border:1px solid #e7ebf2;border-radius:14px;padding:14px 16px;margin-bottom:10px}");
            b.append(".n{font-weight:600}.m{color:#8a93a0;font-size:12px;margin-top:2px}");
            b.append("a{display:inline-block;margin-top:8px;background:#2f6bff;color:#fff;text-decoration:none;");
            b.append("padding:7px 14px;border-radius:9px;font-size:13px}");
            b.append(".f{color:#9aa3b0;font-size:12px;margin-top:18px}");
            b.append("</style></head><body><div class=\\"w\\">");
            b.append("<h1>").append(esc(game.label)).append(" · Key 列表</h1>");
            b.append("<div class=\\"s\\">共 ").append(l.size()).append(" 个账号 · 只在这台手机上开着这个窗口时能访问</div>");
            for (int i = 0; i < l.size(); i++) {
                Account a = l.get(i);
                b.append("<div class=\\"i\\"><div class=\\"n\\">").append(esc(a.name)).append("</div>");
                b.append("<div class=\\"m\\">指纹 ").append(a.fpShort()).append(" · ").append(a.key.length()).append("B");
                if (a.note != null && a.note.length() > 0) b.append(" · ").append(esc(a.note));
                b.append("</div><a href=\\"/key?i=").append(i).append("&k=").append(code).append("\\">下载 AuthKey.txt</a></div>");
            }
            b.append("<div class=\\"f\\">下载下来的是原始的 key 文本，放进游戏对应的 AuthKey 路径即可。关掉 App 里的窗口后这个页面就打不开了。</div>");
            b.append("</div></body></html>");
            return b.toString();
        }

        private String esc(String s) {
            if (s == null) return "";
            return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\\"", "&quot;");
        }
    }

'''
rep(anchor, methods + anchor)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("patched", len(orig), "->", len(s))