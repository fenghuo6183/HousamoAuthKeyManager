# <img src="docs/icon.png" width="64" align="top"> 东放 AuthKey 管家 (Housamo AuthKey Manager)

给《东京放课后召唤师》(東京放課後サモナーズ / Housamo, 包名 `jp.co.lifewonders.housamo`) 用的 **一键备份 / 迁移 / 多开** 工具。

> 社区里说的 **aunkey** 就是游戏的 **AuthKey**：一个几十~几百字节的文本文件，游戏用它记住「你是哪个账号」。删掉它，游戏会当成新号重新生成；把它复制回原位，游戏就登回原账号。本工具做的事就是**把这个文件安全地取出来、存好、再写回去**。

![platform](https://img.shields.io/badge/platform-Windows%20%7C%20Android-blue) ![license](https://img.shields.io/badge/license-MIT-lightgrey)

---

## 功能

- **一键提取**：连上手机 / 模拟器，点一下就把当前账号的 AuthKey 抓进账号库（自动带设备名和时间），并立刻导出成文件。
- **一键导入**：选中账号 → 自动停游戏 → 自动备份原有 key → 写入 → 回读校验，启动游戏即登录。
- **多账号管理**：重命名、指纹校验、删除、明文 `.hak` 导入导出（换电脑 / 备份用）。
- **提取即命名**：抓到 key 后弹框让你起名，同时保存一份到 `Download/东放Key/<名字>/AuthKey.txt`（Android 端可在设置里改导出位置），文件管理器里直接能看到、能发给别人。
- **保存文件夹（Windows）**：选一个文件夹，之后每次提取都自动按账号名建子文件夹写 `AuthKey.txt`。
- **模拟器多开**：自动扫描 MuMu / 雷电 / 夜神 / 逍遥 / BlueStacks / 通用 5555 等端口，一台机器多开几个模拟器也能分别提取与导入。
- **免 root 优先**：Android 10 及以下游戏把 AuthKey 放在**外部存储**（`/sdcard/Android/data/...`），无需 root；Android 11+ 系统封了该目录，工具支持 **Shizuku**（把 adb shell 权限借给普通 App，不需要 root）与 **root** 两条通道。

## 仓库结构

```
.
├── win/                      Windows 桌面端（Python + tkinter）
│   ├── main.py               入口（--selftest 无窗自检）
│   ├── app/
│   │   ├── adb.py            adb 封装：设备发现、模拟器端口扫描
│   │   ├── game.py           AuthKey 路径、提取、写入、备份
│   │   ├── vault.py          账号库（DPAPI 加密落盘）
│   │   ├── dpapi.py          Windows DPAPI 加解密封装
│   │   └── ui.py             主界面
│   ├── assets/platform-tools/  内置 adb（由 tools/fetch_toolchain.py 生成）
│   └── build.bat             一键打包 exe
├── android/                  Android 端（Java，无 Gradle 手工构建）
│   ├── AndroidManifest.xml
│   ├── src/com/housamo/authkey/MainActivity.java
│   ├── libs/                 Shizuku API（MIT，vendor 进来免 Gradle 依赖）
│   ├── res/                  启动图标（自适应图标 + 各密度 png，由 tools/gen_icon.py 生成）
│   └── build_apk.py          aapt2 + javac + d8 + zipalign + apksigner
└── tools/                    开发期工具（拉取 JDK / SDK / PyInstaller）
```

## 使用（Windows，推荐）

1. 到 [Releases](../../releases) 下载 `AuthKeyManager-win64.zip`，解压后双击 `AuthKeyManager.exe`（已内置 adb，无需安装 Android SDK）。
2. 手机：设置 → 关于手机 → 连点「版本号」7 次开启开发者选项 → 打开 **USB 调试** → 数据线连电脑 → 手机上点「允许调试」。
   模拟器：直接点界面上的 **扫描模拟器**。
3. 第一次用先在「保存文件夹」那一行点 **选择文件夹**（选好后每次提取都会自动导出到这个文件夹）。
4. 顶部下拉框选中设备 → **提取当前账号的 key** → 弹框里给它起个名字（提取完会直接存一份到第 3 步选的文件夹）。
5. 换号：列表里选中目标账号 → **将当前选择的 key 导入到游戏** → 处理完点 **打开游戏**。

> 账号库默认加密保存在 `%APPDATA%\HousamoAuthKey\vault.dat`（Windows DPAPI，只有当前 Windows 用户能解开）。要换机器 / 备份就用「导出 .hak」，那是明文，**别随便发给别人**。

## 使用（Android）

下载 Release 里的 `HousamoAuthKeyManager-1.0.10.apk` 安装（Android 7.0+）。

- **有 root**：直接用，提取 / 导入都走 root 通道。
- **无 root + Shizuku（推荐给只在手机上操作的）**：
  1. 安装并启动 [Shizuku](https://shizuku.rikka.app/)。首次需要通过「开发者选项 → 无线调试」配对启动（Shizuku 自己是靠 adb 权限起的，**不需要 root**；网上有大量图文教程）。
  2. 打开本 App，在「首页 → 权限管理」里点 **Shizuku 权限** → 在 Shizuku 弹窗里点「允许」。
  3. 状态变成「Shizuku 已授权」后，提取 / 导入即可正常工作（走 shell 通道，等同 `adb pull`）。
  4. 没装 Shizuku 时点这一行会直接问你要不要跳转下载；装了但服务没起，会帮你把 Shizuku 打开。

界面分四个页签：

- **首页**（照 MAA 的排版做的）：屏幕分辨率 / 游戏版本 / App 版本 / 服务状态，运行模式，以及权限管理（Shizuku、Root、外部存储、电池优化白名单、通知）。权限那几行点一下就能去授权，返回后自动刷新。
- **任务**：三个按钮——「提取当前账号的 key」「将当前选择的 key 导入到游戏」「把选中的 key 再存一份到文件夹」；最上面那张卡就是存到哪个文件夹，点一下就能换。下面还有一张**「导入前备份」**卡，显示上一次导入前自动备份的完整路径。最下面是运行日志，每一步都有记录，出问题先看这里。
- **账号**：顶部两个分段「账号 / 备份」——**账号**只放你自己提取或从导出文件夹扫到的 key（卡片显示名字、指纹、大小、导入时间、存盘路径），选中后可复制 / 重命名 / 删除；**备份**单独一栏，只放每次导入前自动存下的原 key，选中点「导入到游戏」即可还原，不会和账号混在一起。两个分段都显示数量，长按卡片也能直接复制（备份则直接导入）。换手机、清了 App 数据，只要导出文件夹还在，进来点「重新扫描 key」就能把账号全部找回来。
- **设置**：权限、导出位置、检查更新、项目主页（点一下跳 GitHub）、版本、清空账号库。

**自动检查更新（App 内直接更新）**：每次打开 App 会自动去 GitHub 查最新 Release，**有新版就直接弹窗提示**（不藏在设置里）。点「立即更新」会当场下载 APK 并调起系统安装器覆盖安装，账号库和导出文件夹里的 key 都不动；如果系统还没允许「安装未知应用」，会先带你去开那个开关，回来自动继续装。设置页的「检查更新」也能手动触发，另有「去网页」按钮可走浏览器。

**导出位置可自选**：设置 → 导出位置 → 选一个文件夹（默认 `Download/东放Key/`），之后每个账号都会在下面建一个以账号名命名的子文件夹，里面放 `AuthKey.txt`。

**导入前一定先备份**：每次点「导入」时，App 会先把**游戏里正在用的 key** 原样存一份到 `Download/东放Key/导入前备份/AuthKey-MMdd-HHmmss-<指纹>.txt`，同时往账号库里加一条「导入前备份 <时间>」记录，然后才写入你选的 key。写完会回读校验；万一写入失败，会尝试把原 key 写回去，并在日志里说明。**换号换错了想换回去，去这个备份目录拿最新那个文件导入即可**。备份是明文，请自己保管，别随手发人。这些备份现在单独列在账号页的「备份」分段里，不再混在账号列表里。

**备份写不出来就不导入**：如果备份那一步没成功（没存储权限、空间满了等），导入会被**直接中止**，绝不会在没备份的情况下覆盖你现在登录的 key，日志里会写明原因。

**首次启动的免责声明**：第一次打开 App 会弹一个说明，必须**滚到底 + 等满 10 秒**「同意」按钮才会亮，点退出则关闭 App。里面写清了：本工具只复制文件、key 等同账号密码、备份文件在哪、覆盖风险、非官方工具、禁止盗号。

提取完会让你给账号起个名字，key 会同时进账号库，并写出 `<导出位置>/<你起的名字>/AuthKey.txt`。
- **无 root 且没有 Shizuku**：只有 Android 10 及以下能直接读写外部 AuthKey；**Android 11 及以上系统不允许任何 App 访问 `Android/data/<其它包名>`**，请改用 Windows 版（adb 免 root）。

## AuthKey 到底在哪

| 平台 | 路径 | 需要 root |
| --- | --- | --- |
| Android | `/sdcard/Android/data/jp.co.lifewonders.housamo/files/Data/AuthKey` | 否（Android ≤10） |
| Android | `/data/data/jp.co.lifewonders.housamo/shared_prefs/jp.co.lifewonders.housamo.v2.playerprefs.xml` | 是 |
| iOS | `/var/mobile/Containers/Data/Application/<UUID>/files/Data/AuthKey` | 越狱 |

提取顺序：外部 AuthKey → root 读外部 → root 读 shared_prefs → `find` 全盘扫描兜底。

## 模拟器端口

| 模拟器 | 端口 |
| --- | --- |
| MuMu 12 | 16384 / 7555 |
| 雷电 | 5555 / 5557 / 5559 / 5565 |
| 夜神 | 62001 / 62025 / 62026 |
| 逍遥 | 21503 |
| BlueStacks | 5555 / 5565 / 5575 |
| WSA | 58526 |
| 通用 | 5555 / 5556 |

## 自己构建

**Windows 端**

```bat
python tools/fetch_toolchain.py       :: 下载 JDK / cmdline-tools / platform-tools，并复制 adb 到 win/assets
cd win
python main.py                        :: 源码运行
python main.py --selftest             :: 无窗口自检
pip install pyinstaller && build.bat  :: 打包 exe -> dist\AuthKeyManager\
```

**Android 端**（不需要 Gradle）

```bash
python tools/fetch_toolchain.py    # JDK 17 + cmdline-tools + platform-tools
python tools/fetch_sdk_packages.py # platform-34 + build-tools 34.0.0
python android/build_apk.py        # -> dist/HousamoAuthKeyManager-1.0.10.apk（Shizuku api 13.1.0 已 vendor 在 android/libs）
```

## 常见问题

**提取不到 key？**
先用游戏正常登录一次（key 才会生成）；确认设备已授权调试；Android 11+ 且没有 root 时，用 Windows 版走 adb，或者在手机上装 Shizuku 并点 App 里的「Shizuku」按钮授权。

**Shizuku 一直显示「未连接」？**
Shizuku 服务没起来（重启手机后要重新用无线调试启动一次），先打开 Shizuku App 确认它是运行状态，再回到本 App 点「刷新状态」。

**导入后游戏还是新号？**
导入前必须让游戏进程完全退出（工具会 `am force-stop`），否则游戏退出时会用内存里的状态覆盖文件。导入完再启动游戏。

**会不会被封号？**
本工具只做文件复制，不修改内存、不注入、不自动签到、不联网。账号备份 / 多开是社区长期做法，但**风险自负**，详见免责声明。

**账号库安全吗？**
Windows 端用 DPAPI 加密，绑定当前 Windows 账号；Android 端存在应用私有 SharedPreferences。导出的 `.hak` 是明文，请自行保管。

## 免责声明

本项目仅供**账号备份、迁移与多开**用途，与 LifeWonder 无关，非官方工具。请勿用于买卖账号、代练、外挂等违反游戏用户协议的行为。使用本工具造成的账号异常、数据丢失等后果由使用者自行承担。若官方提出异议，将立即停止维护。

## 更新日志

- **v1.0.10** — 全新应用图标：把角色立绘做成自适应图标（Android 8+ 各种圆/方/水滴形状里都能正确裁切，低版本用传统方形图标）；设置页与桌面图标保持一致。
- **v1.0.9** — 账号页改版：账号与备份分成两个分段、各自独立列表；账号卡片重做（加粗名称 + 指纹/大小/时间 + 存盘路径 + 选中勾选圈），备份卡片标成琥珀色并支持「导入到游戏」一键还原；修掉长按在备份页会复制 key 的行为。
- **v1.0.8** — 修掉设置页「版本」写死成 1.0.5 的显示错误，现在直接读系统里的真实版本号（如 1.0.8 (9)）；其余与 1.0.7 相同。
- **v1.0.7** — 支持 App 内直接更新：启动发现新版本就弹窗，点「立即更新」当场下载并覆盖安装（不再跳浏览器）；**备份失败则中止导入**，绝不在没备份的情况下覆盖原 key。
- **v1.0.6** — 账号页自动读取导出文件夹里的 key（App 数据丢了文件夹还在就能恢复）；导入前自动备份原 key 到 `Download/东放Key/导入前备份/`，任务页显示最近一次备份路径，写入失败会自动回写原 key；首次启动弹免责声明，必须读完并等满 10 秒才能同意；Windows 端按钮文案同步改成「提取当前账号的 key」「将当前选择的 key 导入到游戏」。
- **v1.0.5** — 设置页补上「项目主页」一键跳转；每次启动自动检查更新；修掉若干界面细节。
- **v1.0.4** — 界面文案与排版微调。
- **v1.0.3** — 界面重做成白卡三页签（任务 / 账号 / 设置）；提取后可自己命名，并导出到 `Download/东放Key/<名字>/AuthKey.txt`；Windows 端可选择保存文件夹，提取后自动按名字分文件夹保存；写 AuthKey 改为原地覆盖（`cat >`），保留原属主与权限，避免 `cp` 后文件变成 shell 所有导致游戏读不到。
- **v1.0.2** — Android 端接入 Shizuku，无 root 也能在手机上提取 / 导入；最低系统要求升到 Android 7.0。
- **v1.0.1** — 修复 Android 11+ 包可见性导致「游戏：未检测到」。
- **v1.0.0** — 首发：Windows 桌面端 + Android 端。

## 致谢

- [Shizuku](https://github.com/RikkaApps/Shizuku-API)（MIT）—— 免 root 的 shell 通道。
- 社区里关于 AuthKey 路径的各种总结。

## License

MIT
