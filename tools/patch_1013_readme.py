# -*- coding: utf-8 -*-
import io
R = "D:/123/4/README.md"
s = io.open(R, encoding="utf-8").read()
o = len(s)

def rep(old, new, why):
    global s
    n = s.count(old)
    assert n == 1, "count=%d %s" % (n, why)
    s = s.replace(old, new, 1)

rep("- **多账号管理**：重命名、指纹校验、删除、明文 `.hak` 导入导出（换电脑 / 备份用）。",
"- **多账号管理**：重命名、指纹校验、删除、明文 `.hak` 导入导出（换电脑 / 备份用）。\n- **两个游戏都支持**：《东京放课后召唤师》和 LiveAHero——两个游戏的账号、备份、导出文件夹**完全分开**，顶部点一下就切，不会混在一起、更不会互相覆盖。", "feature bullet")

rep("下载 Release 里的 `HousamoAuthKeyManager-1.0.12.apk` 安装（Android 7.0+）。",
"下载 Release 里的 `HousamoAuthKeyManager-1.0.13.apk` 安装（Android 7.0+）。", "apk name")

rep("最上面的「当前账号」一行点一下就跳到账号页挑 key，下面两个操作都针对它。",
"顶部先是一张「游戏」卡（东京放课后 / LiveAHero 一点就切），下面「当前账号」一行点一下跳到账号页挑 key，再下面两个操作都针对它。", "task bullet")

rep("**自动检查更新（App 内直接更新）**：",
"""**两个游戏都支持（东京放课后 / LiveAHero）**：任务页和账号页顶部各有一张「游戏」卡，点一下切换。两个游戏的数据完全隔离——切过去只看到那个游戏自己的账号和备份，导入也只会写进当前这个游戏，不会把东放的 key 写进 LiveAHero。导出目录分别是 `Download/东放Key/`（东放，沿用老路径，老用户升级后已有文件原地不动）和 `Download/东放Key/LiveAHero/`。LiveAHero 的 key 在 `/sdcard/Android/data/jp.co.lifewonders.liveahero/files/datas/userKey`，和 Housamo 的 AuthKey 是同一套机制、同样大小，所以提取 / 导入 / 备份全都能用。

**每次打开都对一次账（启动核对）**：App 回到前台时会读一次当前游戏正在用的 key，如果账号库里找不到它（换过号、清过数据、或者从别处拿了个 key 直接覆盖），任务页顶部立刻出现一张黄色提示卡，写明「游戏里现在用的指纹是 xxx，账号库里没有这个 key」。想留一份就点「存到账号库」，会存成一条「游戏内快照 <时间>」并导出到文件夹；不想留点「不用管」，同一个指纹之后不再打扰。**它只提示、不自动存**，不会往账号库里塞你没要的东西。

**自动检查更新（App 内直接更新）**：""", "multi-game section")

rep("换手机、清了 App 数据，只要导出文件夹还在，进来点「重新扫描 key」就能把账号全部找回来。",
"启动核对里点「存到账号库」生成的「游戏内快照 <时间>」也在这里，跟普通账号一样能导入 / 改名 / 删除。换手机、清了 App 数据，只要导出文件夹还在，进来点「重新扫描 key」就能把账号全部找回来（只会扫当前这个游戏的目录）。", "account notes")

rep("python android/build_apk.py        # -> dist/HousamoAuthKeyManager-1.0.12.apk（Shizuku api 13.1.0 已 vendor 在 android/libs）",
"python android/build_apk.py        # -> dist/HousamoAuthKeyManager-1.0.13.apk（Shizuku api 13.1.0 已 vendor 在 android/libs）", "build cmd")

rep("- **v1.0.12** —",
"""- **v1.0.13** — **多游戏支持**：新增 LiveAHero（`jp.co.lifewonders.liveahero`），任务页和账号页顶部各有一张「游戏」切换卡，两个游戏的账号 / 备份 / 导出文件夹完全隔离（后装的游戏导出到 `Download/东放Key/LiveAHero/`，东放沿用老路径、老数据不动）；没装的那个游戏按钮会是半透明、并提示未安装。新增**启动核对**：每次回到 App 都读一次游戏里正在用的 key，账号库里没有的话在任务页顶上弹一张黄色提示卡，写明当前指纹，点「存到账号库」才存成「游戏内快照 <时间>」，点「不用管」则同一指纹不再打扰——只提示不自动存，不会塞一堆你没要的条目。

- **v1.0.12** —""", "changelog")

io.open(R, "w", encoding="utf-8").write(s)
print("readme ok", o, "->", len(s))
