# AGENTS.md — 给后续 Agent 的交接说明

本项目是「东放 AuthKey 管家」：Windows 桌面端（Python + Qt，入口 `win/qt_main.py`）与 Android 端（纯 Java，手工构建、无 Gradle，入口 `android/src/com/housamo/authkey/MainActivity.java`）的组合工具，用来备份 / 迁移《东京放课后召唤师》与 LiveAHero 的 AuthKey。

功能、使用方法和截图先读 `README.md`；本文件只写**做改动时必须遵守的约定**。

## 硬性约定

1. **两端同号**：`win/app/theme.py` 的 `APP_VERSION` 是唯一版本基准。每次发版必须同步四处：

   | 位置 | 字段 |
   | --- | --- |
   | `win/app/theme.py` | `APP_VERSION`（基准） |
   | `android/AndroidManifest.xml` | `android:versionName`、`android:versionCode` |
   | `android/build_apk.py` | `VERSION_NAME`、`VERSION_CODE` |
   | `android/src/com/housamo/authkey/MainActivity.java` | `CURRENT_VER` |

   `versionCode` 每发一版 +1。改完跑 `python tools/check_version.py` 核对。

2. **功能两端一起做**：用户提的功能，Windows（`win/`）和 Android 都要实现，落点和提示口径保持一致。只改一边的功能不发版。Bug 修复如果只影响一端，要在 `docs/DEVLOG.md` 里写明「另一端为什么不用改」。

3. **发版流程**见 `README.md` 的「发版流程（两端同号）」一节。Windows 正式包构建用：

   ```powershell
   cd win
   python -m PyInstaller --noconfirm --clean AuthKeyManager.spec   # 输出 win/dist/AuthKeyManager
   cd ..
   python tools/make_win_zip.py                                    # 输出 dist/AuthKeyManager-win64.zip
   python android/build_apk.py                                     # 输出 dist/HousamoAuthKeyManager-<版本>.apk
   ```

4. **每次改动都要登记（用户 2026-11-28 明确要求）**：每完成一次代码 / 行为改动，在 `docs/DEVLOG.md` 末尾追加一条记录，格式见该文件开头。不要只在聊天里说明；README 的「更新日志」是面向用户的发布说明，不能代替 DEVLOG。

## 常用命令

```powershell
cd win
python -m unittest discover -s tests -p "test_*.py"   # Windows 端单测，全绿再发版
python main.py --selftest                             # 旧 Tk 版无窗自检（正式版是 Qt）
```

## 目录速览

```
win/        Windows 端（Qt 界面的正式版入口 qt_main.py；app/ 里是业务逻辑）
android/    Android 端（Java + aapt2/javac/d8/apksigner 手工构建）
docs/       图标、截图，以及本文件的改动记录 DEVLOG.md
tools/      开发期工具（拉取 JDK / SDK / PyInstaller、版本核对、发布脚本）
```
