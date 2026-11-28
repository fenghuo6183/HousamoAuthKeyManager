# -*- coding: utf-8 -*-
import io
P = "README.md"
s = io.open(P, encoding="utf-8").read()

anchor = '- **免 root 优先**：Android 10 及以下游戏把 AuthKey 放在**外部存储**（`/sdcard/Android/data/...`），无需 root；Android 11+ 系统封了该目录，工具支持 **Shizuku**（把 adb shell 权限借给普通 App，不需要 root）与 **root** 两条通道。'
add = anchor + '''
- **四种导入方式（Android）**：文件夹批量导入（选中目录，把里面所有 AuthKey 收进账号库）、**从剪贴板导入**（群里发的一串 key 直接粘进来）、**从二维码图片导入**（截图里扫出来的码）、以及原有的「导入到游戏」。
- **账号备注 / 复制指纹 / 生成二维码（Android）**：长按账号有完整菜单；备注写「日服小号」这类随手说明，复制指纹方便跟人对账，生成二维码可以直接发给另一台设备扫。
- **撤销这次导入 + 导入历史（Android）**：导入完成的弹窗上就有「撤销这次导入」，一键写回原来的 key；设置页的「导入历史」记着每次换了谁、之前的 key 备份在哪，点一条也能回退。
- **备份保留策略（Android）**：可选「全部保留 / 最近 10 份 / 最近 30 天」，超过的自动清理（默认全部保留，不会擅自删东西）。
- **打包导出全部 key（Android）**：一次选目录，把账号库里所有 key 打成一个 zip（附 `manifest.txt` 清单：指纹、字节数、创建时间、备注），换机时省事。
- **局域网传输（Android）**：手机和电脑同一个 WiFi，在 App 里打开「局域网传输」，电脑浏览器打开显示的地址就能看到账号列表并直接下载 key，配对码错的人打不开，关掉窗口即停止。
- **深色模式 / 应用锁 / 防止截屏（Android）**：设置页可切深色配色；应用锁是 4-6 位数字密码，回到 App 需要解锁；防止截屏打开后系统截图和录屏都是黑的。
- **首页账号概览（Android）**：一进来就能看到游戏里正在用的 key 指纹、上次自动备份的时间、账号/备份数量，点一下跳对应页面。'''
assert s.count(anchor) == 1
s = s.replace(anchor, add)

s = s.replace("到 [v1.0.17 Release](../../releases/tag/v1.0.17) 下载 `HousamoAuthKeyManager-1.0.17.apk` 安装（Android 7.0+）。",
              "到 [v1.0.18 Release](../../releases/tag/v1.0.18) 下载 `HousamoAuthKeyManager-1.0.18.apk` 安装（Android 7.0+）。")
s = s.replace("python android/build_apk.py        # -> dist/HousamoAuthKeyManager-1.0.17.apk",
              "python android/build_apk.py        # -> dist/HousamoAuthKeyManager-1.0.18.apk")

log_anchor = "- **v1.0.17** — **从一个文件夹导入 key**"
entry = '''- **v1.0.18** — **一口气加了 13 项功能**：①从剪贴板导入 key（含整段 playerprefs xml）②账号备注 ③账号页也有「从文件夹导入」入口 ④长按复制指纹 ⑤修掉账号页「N 个备份」和分段数字对不上的计数 bug ⑥导入完成可「撤销这次导入」⑦应用锁（4-6 位数字密码）+ 防止截屏 ⑧导入历史时间线（可点一条回退）⑨自动备份保留策略（全部 / 最近 10 份 / 最近 30 天）⑩打包导出全部 key 为 zip（带 manifest 清单）⑪生成 / 扫描二维码导入 ⑫局域网传输（电脑浏览器直接下载 key）⑬深色模式 ⑭首页账号概览卡。另外把「检查更新」改成只认带 APK 的 Release——之前 Windows 端的 `v1.1` 发布会让手机版误以为要更新。
'''
assert s.count(log_anchor) == 1
s = s.replace(log_anchor, entry + log_anchor)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("readme ok", len(s))