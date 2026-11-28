# -*- coding: utf-8 -*-
import io
P = "README.md"
s = io.open(P, encoding="utf-8").read()
n = 0
def rep(old, new):
    global s, n
    assert s.count(old) == 1, (s.count(old), old[:60])
    s = s.replace(old, new)
    n += 1

rep('- **首页账号概览（Android）**：一进来就能看到游戏里正在用的 key 指纹、上次自动备份的时间、账号/备份数量，点一下跳对应页面。',
    '''- **首页账号概览（Android）**：一进来就能看到游戏里正在用的 key 指纹、上次自动备份的时间、账号/备份数量，点一下跳对应页面。
- **整页可滑动 + 底部图标（Android）**：首页 / 任务 / 设置三页都套了滚动容器，小屏手机上也能滑到最下面，不会被截断；底部四个菜单配了图标（首页 / 任务 / 账号 / 设置），选中时文字和图标一起变蓝。
- **每一行都有按钮（Android）**：权限、外观、安全三张卡不再靠「整行能点」这种看不出来的交互——Shizuku 授权、存储权限、重新检测、深色模式、应用锁、防止截屏，右边都是明确的蓝色按钮，按钮文字跟着状态变（已开启就显示「关闭」）。''')

rep('到 [v1.0.18 Release](../../releases/tag/v1.0.18) 下载 `HousamoAuthKeyManager-1.0.18.apk` 安装（Android 7.0+）。',
    '到 [v1.0.19 Release](../../releases/tag/v1.0.19) 下载 `HousamoAuthKeyManager-1.0.19.apk` 安装（Android 7.0+）。')
rep('python android/build_apk.py        # -> dist/HousamoAuthKeyManager-1.0.18.apk',
    'python android/build_apk.py        # -> dist/HousamoAuthKeyManager-1.0.19.apk')

anchor = '- **v1.0.18** — **一口气加了 13 项功能**'
entry = '''- **v1.0.19** — **界面顺手了**：①首页 / 任务 / 设置三页改成整页可滑动，小屏也不会「下面那截看不见」②底部四个菜单加上图标（房子 / 清单 / 人 / 滑块），选中时图标和文字一起变蓝 ③设置页权限、外观、安全三张卡的每一行都加了明显的蓝色按钮——Shizuku「授权」、存储「去设置」、重新检测「刷新」、深色模式「切到深色 / 切到浅色」、应用锁「开启 / 关闭」、防止截屏「开启 / 关闭」④安全两行还会写清当前状态（比如「已禁止：系统截图和录屏是黑的」）；关应用锁要先输一次现在的密码。
'''
rep(anchor, entry + anchor)

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("readme", n, len(s))