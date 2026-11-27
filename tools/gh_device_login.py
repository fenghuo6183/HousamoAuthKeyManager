# -*- coding: utf-8 -*-
"""GitHub OAuth device flow login (same public client id the gh CLI uses)."""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

CLIENT_ID = "Iv1.b507a08c87ecfe98"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = os.path.join(ROOT, ".tmp")


def post(url, data, tries=6):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(
                url,
                data=urllib.parse.urlencode(data).encode(),
                headers={"Accept": "application/json",
                         "User-Agent": "HousamoAuthKeyManager",
                         "Connection": "close"})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.load(r)
        except Exception as e:
            last = e
            time.sleep(3 + i * 2)
    raise SystemExit("network error: %r" % (last,))


def save(name, obj):
    os.makedirs(TMP, exist_ok=True)
    with open(os.path.join(TMP, name), "w") as f:
        json.dump(obj, f)


def main():
    d = post("https://github.com/login/device/code", {"client_id": CLIENT_ID, "scope": "repo"})
    save("device.json", d)
    print("CODE:" + d["user_code"], flush=True)
    print("URL:" + d["verification_uri"], flush=True)
    interval = int(d.get("interval", 5))
    deadline = time.time() + int(d["expires_in"])
    while time.time() < deadline:
        time.sleep(interval)
        r = post("https://github.com/login/oauth/access_token", {
            "client_id": CLIENT_ID,
            "device_code": d["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"})
        err = r.get("error")
        if err == "authorization_pending":
            continue
        if err == "slow_down":
            interval += 5
            continue
        if err:
            print("ERROR:" + err + " " + str(r.get("error_description")), flush=True)
            return 1
        os.makedirs(TMP, exist_ok=True)
        with open(os.path.join(TMP, "gh_token.txt"), "w") as f:
            f.write(r["access_token"])
        print("TOKEN_SAVED", flush=True)
        return 0
    print("ERROR:expired", flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
