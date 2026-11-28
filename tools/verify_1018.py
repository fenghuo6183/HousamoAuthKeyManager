# -*- coding: utf-8 -*-
import json,io,urllib.request,hashlib,base64
TOK=io.open('.tmp/gh_token.txt').read().strip()
def api(m,p,body=None):
    rq=urllib.request.Request('https://api.github.com'+p, method=m,
        data=None if body is None else json.dumps(body).encode(),
        headers={'Authorization':'token '+TOK,'User-Agent':'x','Accept':'application/vnd.github+json','Content-Type':'application/json'})
    return json.load(urllib.request.urlopen(rq,timeout=40))

rel=api('GET','/repos/fenghuo6183/HousamoAuthKeyManager/releases/tags/v1.0.18')
a=rel['assets'][0]
print('asset',a['name'],a['size'],a['digest'])
local=hashlib.sha256(open('dist/HousamoAuthKeyManager-1.0.18.apk','rb').read()).hexdigest()
print('local sha256',local,'match',a['digest']=='sha256:'+local)

# 把 Windows 客户端的 v1.1 改名为 win-v1.1，避免和手机版版本号混淆
old=api('GET','/repos/fenghuo6183/HousamoAuthKeyManager/releases/tags/v1.1')
print('rename',old['tag_name'],'->','win-v1.1')
new=api('PATCH','/repos/fenghuo6183/HousamoAuthKeyManager/releases/%d'%old['id'],{'tag_name':'win-v1.1','name':'Windows 客户端 v1.1'})
print('now',new['tag_name'],new['name'],new['html_url'])
