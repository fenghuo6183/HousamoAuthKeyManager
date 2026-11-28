# -*- coding: utf-8 -*-
import io
P = 'README.md'
s = io.open(P, encoding='utf-8').read()

s = s.replace('HousamoAuthKeyManager-1.0.16.apk', 'HousamoAuthKeyManager-1.0.17.apk')
s = s.replace('dist/HousamoAuthKeyManager-1.0.16.apk', 'dist/HousamoAuthKeyManager-1.0.17.apk')

old_task = '- **任务**：只做两件事——「提取当前账号的 key」和「把选中的 key 复制到其他文件夹」（复制一份保留原件，或直接移动过去、把导出文件夹里那份删掉）。'
assert old_task in s
new_task = '- **任务**：三件事——「提取当前账号的 key」「把选中的 key 复制到其他文件夹」（复制一份保留原件，或直接移动过去、把导出文件夹里那份删掉）「从一个文件夹导入 key」（选一个文件夹，把里面和子文件夹里的 AuthKey 一次全加进账号库，只是进「账号」分段，不会碰游戏里正在登录的账号；已经在库里的 key 自动跳过）。'
s = s.replace(old_task, new_task, 1)

anchor = '## 更新日志\n'
assert anchor in s
entry = ('## 更新日志\n\n'
    '- **v1.0.17** — **从一个文件夹导入 key**：任务页新增第三张卡。点「从一个文件夹导入 key」，用系统文件选择器选一个目录（`Download/东放Key` 这种备份目录、U 盘、网盘目录都行），App 会把该目录和它下面几层子文件夹里看着像 key 的文件全读出来——名字带 `key` / `authkey`、或者 `.txt` / 无扩展名的文件，内容是 16~512 位不含空格的字符串才算；顺手也认 playerprefs.xml。扫完先弹一张卡片，列清楚「找到 N 个、每个的指纹和字节数、其中几个已经在库里会被跳过」，你点「全部导入」才真的写进**「账号」分段**——只是进账号库，游戏里正在登录的账号一点不动；要真切换登录，还是去账号页选中它、点底部蓝色「导入到游戏」（导入前照旧自动备份现在的 key）。Android 11+ 的文件选择器有时不让 App 直接遍历目录，这时会自动改用存储路径再扫一遍，不需要你额外授权。导入的账号名默认取它所在的文件夹名，重名会自动加 ` 2`。\n')
s = s.replace(anchor, entry, 1)

io.open(P, 'w', encoding='utf-8').write(s)
print('readme updated', len(s))