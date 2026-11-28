# 开发改动记录（DEVLOG）

给后续 Agent / 开发者看的**逐次改动流水账**。用户要求（2026-11-28）：每次改动都要写进来，方便其他 Agent 接手时知道「改了什么、为什么、验证过什么」。

## 写法

每次完成代码或行为改动后，在文件末尾追加一节，包含：

- 日期、版本、平台（Windows / Android / 两端）
- **现象与根因**（Bug）或**动机**（功能）
- **改动文件 + 具体做法**（写清楚函数 / 关键行，方便 grep）
- **验证**（跑过的命令与结果；没验证的部分要写明）
- **兼容性 / 升级注意**（账号库、路径、权限、版本号等）

只改一端时，写明另一端为什么不用改。

---

## 2026-11-28 — 未发布 · 并入 v1.1 — Android：切换深色 / 浅色后不再跳回首页

- **现象**：手机上在「设置 → 外观」点「切到深色 / 切到浅色」，界面重建后总是回到「首页」，没有停在设置页。换背景图、清除背景图也走重建，同样会跳回首页。
- **根因**：`MainActivity.buildUi()` 末尾固定调用 `showPage(0)`，而 `showPage()` 会把当前页写进 SharedPreferences。`onCreate()` 是先 `setContentView(buildUi())`、再读 `page` 偏好；读完之前偏好已经被改成 0，于是永远恢复成首页。
- **改动**：`android/src/com/housamo/authkey/MainActivity.java`
  - `showPage(int idx)` 改为调用 `showPage(idx, true)`；新增 `showPage(int idx, boolean remember)`，`remember=false` 时只切换显示、不写偏好。
  - `buildUi()` 末尾改为 `showPage(getPreferences(MODE_PRIVATE).getInt("page", 0), false)`：恢复上次停留的页面，且不覆盖偏好；页 2 的 `refreshCurrentFp()` 只在 `remember=true` 时触发，之后 `onCreate()` 里的正式 `showPage(startPage)` 会补上刷新。
- **验证**：`python android/build_apk.py` 编译通过（aapt2 / javac / d8 / zipalign / apksigner 全过，签名校验正常）。当时没有连接手机或模拟器，未做真机点击验证。
- **另一端**：Windows 端主题切换原本就是「切换后重启程序生效」（`win/qtui/pages.py` 的 `theme_seg`），不存在同一次 Activity 重建的场景，本次没有改 Windows 代码；仍按两端同号惯例把版本号同步到 1.2，并重出 Windows 包。
- **兼容性**：只影响页面恢复逻辑，不碰账号库、导出路径、权限与导入/导出流程；旧版本升级无需迁移。版本号保持 1.1 / versionCode 32，随 v1.1 一起发布。

> 事后更正：这次修复一度被我误按 v1.2 / versionCode 33 发了 Release，同日按用户要求撤回（Release 与 tag 已删除，版本字段回到 1.1 / 32，修复代码保留）。教训：**发版前必须得到用户明确确认，不要自行升版本号**。
