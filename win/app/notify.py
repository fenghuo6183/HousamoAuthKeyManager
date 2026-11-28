"""Outbound notifications: tray balloon (handled elsewhere) and webhooks."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request


def webhook_body(url, title, text):
    """Shape the body the way the target service expects."""
    host = ""
    try:
        host = urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        pass
    line = ("%s\n%s" % (title, text)).strip() if title else text
    if "feishu" in host or "lark" in host:
        return {"msg_type": "text", "content": {"text": line}}
    if "dingtalk" in host:
        return {"msgtype": "text", "text": {"content": line}}
    if "discord" in host:
        return {"content": line[:1900]}
    if "slack" in host:
        return {"text": line}
    if "telegram" in host:
        return {"text": line}
    return {"title": title, "text": text}


def post_webhook(url, title, text, timeout=8):
    """POST the notification. Returns (ok, detail)."""
    url = (url or "").strip()
    if not url:
        return False, "还没填 webhook 地址"
    if not url.lower().startswith(("http://", "https://")):
        return False, "webhook 地址要以 http:// 或 https:// 开头"
    body = json.dumps(webhook_body(url, title, text),
                      ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json; charset=utf-8",
                 "User-Agent": "HousamoAuthKeyManager"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            raw = resp.read(400).decode("utf-8", "replace")
            code = getattr(resp, "status", 200)
            if code >= 400:
                return False, "HTTP %s" % code
            return True, raw.strip() or "HTTP %s" % code
    except Exception as exc:
        return False, str(exc)
