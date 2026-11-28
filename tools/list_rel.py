# -*- coding: utf-8 -*-
import json,io,urllib.request
TOK=io.open('.tmp/gh_token.txt').read().strip()
def api(m,p,body=None):
    rq=urllib.request.Request('https://api.github.com'+p, method=m,
        data=None if body is None else json.dumps(body).encode(),
        headers={'Authorization':'token '+TOK,'User-Agent':'x','Accept':'application/vnd.github+json','Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(rq,timeout=40))

rels=api('GET','/repos/fenghuo6183/HousamoAuthKeyManager/releases?per_page=50')
for r in rels:
    print(r['id'], r['tag_name'], '|', r['name'], '|', [a['name'] for a in r['assets']])
