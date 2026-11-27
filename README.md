# 东放 AuthKey 管家 (Housamo AuthKey Manager)

给《东京放课后召唤师》(東京放課後サモナーズ / Housamo, 包名 `jp.co.lifewonders.housamo`) 用的 **一键备份 / 迁移 / 多开** 工具。

> 社区里说的 **aunkey** 就是游戏的 **AuthKey**：一个几十~几百字节的文本文件，游戏用它记住「你是哪个账号」。删掉它，游戏会当成新号重新生成；把它复制回原位，游戏就登回原账号。本工具做的事就是**把这个文件安全地取出来、存好、再写回去**。

![platform](https://img.shields.io/badge/platform-Windows%20%7C%20Android-blue) ![license](https://img.shields.io/badge/license-MIT-lightgrey)

---

## 功能

- **一键提取**：连上手机 / 模拟器，点一下就把当前账号的 AuthKey 抓进账号库，自动带设备名和时间。
- **一键导入**：选中账号 → 自动停游戏 → 自动备份原有 key → 写入 → 回读校验，启动游戏即登录。
- **多账号管理**：重命名、指纹校验、删除、明文 `.hak` 导入导出（换电脑 / 备份用）。
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
│   └── build_apk.py          aapt2 + javac + d8 + zipalign + apksigner
└── tools/                    开发期工具（拉取 JDK / SDK / PyInstaller）
```

## 使用（Windows，推荐）

1. 到 [Releases](../../releases) 下载 `AuthKeyManager-win64.zip`，解压后双击 `AuthKeyManager.exe`（已内置 adb，无需安装 Android SDK）。
2. 手机：设置 → 关于手机 → 连点「版本号」7 次开启开发者选项 → 打开 **USB 调试** → 数据线连电脑 → 手机上点「允许调试」。
   模拟器：直接点界面上的 **扫描模拟器**。
3. 顶部下拉框选中设备 → **提取 AuthKey 到账号库**。
4. 换号：列表里选中目标账号 → **把选中账号导入设备** → 处理完点 **打开游戏**。

> 账号库默认加密保存在 `%APPDATA%\HousamoAuthKey\vault.dat`（Windows DPAPI，只有当前 Windows 用户能解开）。要换机器 / 备份就用「导出 .hak」，那是明文，**别随便发给别人**。

## 使用（Android）

下载 Release 里的 `HousamoAuthKeyManager-1.0.2.apk` 安装（Android 7.0+）。

- **有 root**：直接用，提取 / 导入都走 root 通道。
- **无 root + Shizuku（推荐给只在手机上操作的）**：
  1. 安装并启动 [Shizuku](https://shizuku.rikka.app/)。首次需要通过「开发者选项 → 无线调试」配对启动（Shizuku 自己是靠 adb 权限起的，**不需要 root**；网上有大量图文教程）。
  2. 打开本 App，点顶部 **Shizuku** 按钮 → 在 Shizuku 弹窗里点「允许」。
  3. 状态栏变成「Shizuku：已授权」后，提取 / 导入即可正常工作（走 shell 通道，等同 `adb pull`）。
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
python android/build_apk.py        # -> dist/HousamoAuthKeyManager-1.0.2.apk（Shizuku api 13.1.0 已 vendor 在 android/libs）
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

- **v1.0.2** — Android 端接入 Shizuku，无 root 也能在手机上提取 / 导入；最低系统要求升到 Android 7.0。
- **v1.0.1** — 修复 Android 11+ 包可见性导致「游戏：未检测到」。
- **v1.0.0** — 首发：Windows 桌面端 + Android 端。

## 致谢

- [Shizuku](https://github.com/RikkaApps/Shizuku-API)（MIT）—— 免 root 的 shell 通道。
- 社区里关于 AuthKey 路径的各种总结。

## License

MIT
