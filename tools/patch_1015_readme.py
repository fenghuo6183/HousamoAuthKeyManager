# -*- coding: utf-8 -*-
import io
p = r'D:/123/4/README.md'
s = io.open(p, encoding='utf-8').read()

s = s.replace('HousamoAuthKeyManager-1.0.14.apk', 'HousamoAuthKeyManager-1.0.15.apk')
s = s.replace('dist/HousamoAuthKeyManager-1.0.14.apk', 'dist/HousamoAuthKeyManager-1.0.15.apk')

old_bullet = u'- **无 root 且没有 Shizuku**：只有 Android 10 及以下能直接读写外部 AuthKey；**Android 11 及以上系统不允许任何 App 访问 `Android/data/<其它包名>`**，请改用 Windows 版（adb 免 root）。'
assert old_bullet in s
new_bullet = u'''- **既没有 root 也没装 Shizuku**：别慌，App 会自己告诉你怎么做——首页权限卡下面有一行蓝字，任务页正上方会直接出现一张「还差一步：读写权限」的引导卡（两种办法各配一个「怎么弄」按钮，弄好后点「我已经弄好了，检查一次」这张卡就消失）。点「提取」或「导入」时如果还没有权限，也会弹窗让你二选一，而不是只闪一句 toast。具体两条路：
  - **装 Shizuku**（免 root）：App 里点「怎么弄」会给一份五步图文（装 Shizuku → 连点版本号开开发者选项（小米是连点「OS 版本」）→ 开 USB 调试和无线调试 → 在 Shizuku 里「通过无线调试启动」配对 → 回 App 检查一次）。
  - **用电脑**：App 里点「怎么弄」会给四步说明，并提供「复制 adb 命令」按钮，直接把 `adb pull` 命令拷到剪贴板；执行和导入都在 Windows 版里做，手机不用装任何东西。
  另外**Android 10 及以下**可以不开任何权限直接读写外部 AuthKey；**Android 11 及以上系统不允许任何 App 访问 `Android/data/<其它包名>`**，这时必须用上面两种方式之一。'''
s = s.replace(old_bullet, new_bullet, 1)

old_faq = u'''**提取不到 key？**
先用游戏正常登录一次（key 才会生成）；确认设备已授权调试；Android 11+ 且没有 root 时，用 Windows 版走 adb，或者在手机上装 Shizuku 并点 App 里的「Shizuku」按钮授权。'''
assert old_faq in s
new_faq = u'''**提取不到 key？**
先用游戏正常登录一次（key 才会生成）；确认设备已授权调试；Android 11+ 且没有 root 时，用 Windows 版走 adb，或者在手机上装 Shizuku 并点 App 里的「Shizuku」按钮授权。不知道自己该用哪种方式的话，直接看任务页顶上那张「还差一步：读写权限」卡，两个「怎么弄」按钮里点一个跟着做就行。

**打开就卡住、不知道下一步点哪？**
任务页顶部会自动出现权限引导卡（只在真的没有权限时出现），首页权限卡下面也有一行提示；点「提取 / 导入」还会再弹一次二选一。跟着卡片上的「怎么弄」走即可，弄好之后点「我已经弄好了，检查一次」自动刷新，卡片消失。'''
s = s.replace(old_faq, new_faq, 1)

old_log = u'''## 更新日志

- **v1.0.14**'''
assert old_log in s
new_log = u'''## 更新日志

- **v1.0.15** — **没有 root / 没装 Shizuku 时不再卡壳**：以前只有一句 toast 或者一行红字，新用户根本不知道下一步该干什么。这版在任务页正上方加了一张「还差一步：读写权限」引导卡（有权限时自动隐藏），把两条可行路线摆出来——① Shizuku（免 root）② 电脑 + USB 线，各自配一个「怎么弄」按钮：Shizuku 给五步图文（含小米「连点 OS 版本」这种容易卡住的地方），电脑路线给四步说明外加「复制 adb 命令」按钮。卡片底部有「我已经弄好了，检查一次」，点一下重新检测 root / Shizuku，有权限了卡片立刻消失、账号页的「游戏里现在用的」也自动刷新。点「提取」「导入到游戏」时若仍无权限，不再只闪一句提示，而是弹窗让你从两种方式里选一个。首页权限卡下面也加了一行说明。顺带把构建脚本里 d8 的参数改成先打 jar（类文件太多时会超过 Windows 命令行长度上限）。
- **v1.0.14**'''
s = s.replace(old_log, new_log, 1)

io.open(p, 'w', encoding='utf-8', newline='\n').write(s)
print('readme ok', len(s.encode('utf-8')))
