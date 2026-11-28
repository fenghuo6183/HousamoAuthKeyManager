# -*- coding: utf-8 -*-
import io
P = "D:/123/4/README.md"
s = io.open(P, encoding="utf-8").read()
s = s.replace("HousamoAuthKeyManager-1.0.15.apk", "HousamoAuthKeyManager-1.0.16.apk")
head = "- **v1.0.15** —"
entry = ("- **v1.0.16** — **弹窗全部重做**：之前的提示框是系统默认样式（绿按钮、方角、一堆挤在一起的小字），"
         "这版全部换成自绘的白色圆角卡片——标题 17 号加粗，说明文字换成柔和的灰蓝，多步骤的地方用蓝色数字圆点一步步排下来，"
         "可选的路线做成整块能点的浅灰卡片，主操作是整宽的蓝色圆角按钮，次要操作收在下面一排灰色小字按钮里。"
         "重做的有：应用内更新提示、Shizuku 五步图文、电脑路线、无权限提示、Shizuku 未安装 / 未启动、"
         "导入到游戏的确认框、导入完成、长按账号卡片弹出的菜单、复制到其他文件夹、重命名、删除、清空账号库、给账号取名字。"
         "确认框里会直接写明目标账号的指纹和游戏里现在用的指纹；菜单项旁边加了一行灰字说明这一项到底做了什么。"
         "功能没有任何删减，只是把长相统一了。\n")
assert s.count(head) == 1
s = s.replace(head, entry + head)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("readme ok", len(s))
