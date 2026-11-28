# -*- coding: utf-8 -*-
import io
p = r'D:/123/4/README.md'
s = io.open(p, encoding='utf-8').read()
def rep(old, new, tag):
    global s
    assert s.count(old) == 1, tag + ' count=' + str(s.count(old))
    s = s.replace(old, new, 1)
    print('ok', tag)

rep(u'`Download/东放Key/<名字>/AuthKey.txt`（Android 端可在设置里改导出位置）',
    u'`Download/东放Key/<游戏名>/<名字>/AuthKey.txt`（Android 端可在设置里改导出位置）', 'line17')

rep(u'`HousamoAuthKeyManager-1.0.13.apk`', u'`HousamoAuthKeyManager-1.0.14.apk`', 'download name')

rep(u'导出目录分别是 `Download/东放Key/`（东放，沿用老路径，老用户升级后已有文件原地不动）和 `Download/东放Key/LiveAHero/`。',
    u'导出目录各有一个专属子文件夹：`Download/东放Key/东京放课后/` 和 `Download/东放Key/LiveAHero/`，两边同名账号也不会互相覆盖。东放老版本曾经把账号文件夹直接铺在 `Download/东放Key/` 根下，升级后这些老文件夹原地不动、照样能被识别（账号页里还是原来的路径），只是新导出的文件会进 `东京放课后/` 子文件夹。', 'line79')

rep(u'（默认 `Download/东放Key/`），之后每个账号都会在下面建一个以账号名命名的子文件夹',
    u'（默认 `Download/东放Key/东京放课后/`，切到 LiveAHero 时是 `Download/东放Key/LiveAHero/`），之后每个账号都会在下面建一个以账号名命名的子文件夹', 'line85')

rep(u'原样存一份到 `Download/东放Key/导入前备份/AuthKey-MMdd-HHmmss-<指纹>.txt`',
    u'原样存一份到 `Download/东放Key/<游戏名>/导入前备份/AuthKey-MMdd-HHmmss-<指纹>.txt`', 'line87')

rep(u'dist/HousamoAuthKeyManager-1.0.13.apk', u'dist/HousamoAuthKeyManager-1.0.14.apk', 'build cmd')

newlog = u'## 更新日志' + chr(10) + chr(10) + u'- **v1.0.14** — **东放也有专属文件夹了**：以前只有 LiveAHero 有 `Download/东放Key/LiveAHero/`，东放的账号文件夹直接铺在 `Download/东放Key/` 根下，两个游戏的导出混在一起。这版把东放也收进 `Download/东放Key/东京放课后/`，导出位置、备份位置（`Download/东放Key/东京放课后/导入前备份/`）都跟着变，设置页里能直接看到完整路径。**老文件不会丢**：升级后 `Download/东放Key/` 根下原有的账号文件夹仍然会被扫描识别（账号页里照旧显示老路径），只是新导出的进子文件夹；SAF 自选的导出/备份目录也是同样逻辑。' + chr(10)
rep(u'## 更新日志', newlog, 'changelog')

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('readme bytes', len(s.encode('utf-8')))