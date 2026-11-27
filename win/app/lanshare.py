# -*- coding: utf-8 -*-
"""Tiny LAN web server so a phone on the same Wi-Fi can fetch keys from the PC.

Mirrors the Android app's 局域网传输: the phone opens a page, the page lists
accounts, and each key downloads as AuthKey.txt. Access needs the pairing code,
which is written into the URL.
"""

from __future__ import annotations

import html
import io
import random
import socket
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

def lan_ip():
    """Best-effort IPv4 of this machine on the local network."""
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            probe.connect(("8.8.8.8", 80))
            return probe.getsockname()[0]
        finally:
            probe.close()
    except OSError:
        pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except OSError:
        return None


def _page(label, rows, code):
    items = []
    for index, row in enumerate(rows):
        items.append(
            '<div class="i"><div class="n">%s</div>'
            '<div class="m">%s · %s</div>'
            '<a href="/key?i=%d&amp;k=%s">下载 AuthKey.txt</a></div>'
            % (html.escape(row.get("name") or "未命名"),
               html.escape(row.get("fingerprint") or ""),
               html.escape(row.get("note") or "无备注"),
               index, code))
    if not rows:
        items.append('<div class="i"><div class="n">账号库是空的</div>'
                     '<div class="m">先在电脑上导入或提取一个 key</div></div>')
    return "".join([
        '<!doctype html><html><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>', html.escape(label), ' · 局域网传输</title><style>',
        'body{font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;',
        'background:#f2f3f6;color:#101418;margin:0;padding:24px}',
        '.w{max-width:640px;margin:0 auto}h1{font-size:20px;margin:0 0 4px}',
        '.s{color:#8a93a0;font-size:13px;margin-bottom:18px}',
        '.i{background:#fff;border:1px solid #e7ebf2;border-radius:14px;padding:14px 16px;margin-bottom:10px}',
        '.n{font-weight:600}.m{color:#8a93a0;font-size:12px;margin-top:2px}',
        'a{display:inline-block;margin-top:8px;background:#2f6bff;color:#fff;text-decoration:none;',
        'padding:7px 14px;border-radius:9px;font-size:13px;margin-right:8px}',
        '.f{color:#9aa3b0;font-size:12px;margin-top:18px}',
        '</style></head><body><div class="w">',
        '<h1>', html.escape(label), ' · Key 列表</h1>',
        '<div class="s">共 ', str(len(rows)),
        ' 个账号 · 只在电脑上开着这个窗口时能访问</div>',
        "".join(items),
        '<a href="/zip?k=', code, '">打包下载全部（zip）</a>',
        '<div class="f">东放 AuthKey 管家 · 关掉电脑上的提示窗口就会停止</div>',
        '</div></body></html>'])


def build_zip(rows, label):
    """Zip with one folder per account plus a manifest (shared with bulk export)."""
    from . import bulk
    buffer = io.BytesIO()
    used = set()
    lines = ["# %s 导出" % label, "名称\t指纹\t字节数\t添加时间\t备注"]
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for index, row in enumerate(rows, 1):
            key = row.get("key") or ""
            folder = bulk.safe_folder(row.get("name"), "account-%d" % index)
            base, bump = folder, 2
            while folder.lower() in used:
                folder = "%s (%d)" % (base, bump)
                bump += 1
            used.add(folder.lower())
            zf.writestr(folder + "/AuthKey.txt", key)
            lines.append("%s\t%s\t%d\t%s\t%s" % (
                row.get("name") or folder, row.get("fingerprint") or "", len(key),
                row.get("created_at") or "",
                (row.get("note") or "").replace("\t", " ").replace("\n", " ")))
        zf.writestr("manifest.txt", "\n".join(lines) + "\n")
    return buffer.getvalue()


class LanServer:
    """Serves the account list while the dialog stays open."""

    def __init__(self, provider, label, port=8766):
        self.provider = provider
        self.label = label
        self.port = port
        self.code = "%04d" % (1000 + random.randint(0, 8999))
        self.httpd = None
        self.thread = None

    # -- lifecycle ----------------------------------------------------
    def start(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                pass

            def _send(self, status, body, ctype, extra=None):
                if isinstance(body, str):
                    body = body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                for key, value in (extra or {}).items():
                    self.send_header(key, value)
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                parsed = urlparse(self.path)
                query = parse_qs(parsed.query)
                if (query.get("k") or [""])[0] != server.code:
                    self._send(403, "配对码不对。请用电脑上显示的完整地址打开。",
                               "text/plain; charset=utf-8")
                    return
                rows = server.rows()
                if parsed.path in ("/", ""):
                    self._send(200, _page(server.label, rows, server.code),
                               "text/html; charset=utf-8")
                elif parsed.path == "/key":
                    try:
                        index = int((query.get("i") or ["-1"])[0])
                    except ValueError:
                        index = -1
                    if index < 0 or index >= len(rows):
                        self._send(404, "没有这个账号", "text/plain; charset=utf-8")
                        return
                    self._send(200, rows[index].get("key") or "",
                               "application/octet-stream",
                               {"Content-Disposition": 'attachment; filename="AuthKey.txt"'})
                elif parsed.path == "/zip":
                    self._send(200, build_zip(rows, server.label), "application/zip",
                               {"Content-Disposition": 'attachment; filename="AuthKeys.zip"'})
                else:
                    self._send(404, "not found", "text/plain; charset=utf-8")

        last = None
        for offset in range(20):
            try:
                self.httpd = ThreadingHTTPServer(("0.0.0.0", self.port + offset), Handler)
                self.port = self.port + offset
                self.httpd.daemon_threads = True
                break
            except OSError as exc:
                last = exc
                self.httpd = None
        if self.httpd is None:
            raise RuntimeError("没有可用端口：%s" % last)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self.url()

    def rows(self):
        try:
            return list(self.provider() or [])
        except Exception:
            return []

    def ip(self):
        if self.httpd is None:
            return None
        return lan_ip()

    def url(self):
        ip = self.ip()
        if ip is None:
            return "http://127.0.0.1:%d/?k=%s" % (self.port, self.code)
        return "http://%s:%d/?k=%s" % (ip, self.port, self.code)

    def stop(self):
        httpd, self.httpd = self.httpd, None
        if httpd is None:
            return
        try:
            httpd.shutdown()
        except Exception:
            pass
        try:
            httpd.server_close()
        except Exception:
            pass
