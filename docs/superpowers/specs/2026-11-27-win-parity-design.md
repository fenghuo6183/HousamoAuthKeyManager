# Windows 端功能对齐安卓端（双游戏 · 备份分区 · 启动核对 · 自动更新）

- 日期：2026-11-27
- 状态：待评审
- 影响范围：`win/`（Python + tkinter 桌面端），不涉及 `android/`
- 目标版本：Windows 1.2.0

## 1. 背景

安卓端（`android/src/com/housamo/authkey/MainActivity.java`，约 3447 行）已经具备四项 Windows 端没有的能力：双游戏、导入前备份单独分区、启动核对、App 内检查更新。Windows 端（`win/app/ui.py` 约 1114 行）仍只支持《东京放课后召唤师》单一游戏，账号库里也不区分「账号 / 备份」。

官方《东京放课后召唤师》只发布 iOS / Android，没有 PC 客户端；此处的「端游」指本工具的 Windows 桌面端。本次把四项能力补齐，行为与安卓端一致，实现按 Windows 的习惯重做。

## 2. 范围

**做**

1. 双游戏：东京放课后（`jp.co.lifewonders.housamo`）与 LiveAHero（`jp.co.lifewonders.liveahero`），数据物理隔离。
2. 导入前自动备份：单独归入「备份」分区，可一键还原。
3. 启动核对：读设备上游戏正在用的 key，账号库里没有就提示「存到账号库 / 不用管」。
4. 检查更新：启动后台检查 + 设置页手动检查；下载整包、校验、退出后替换、重启生效、失败下次启动自修复；支持镜像源。

**不做**

- 不改安卓端代码；不做 iOS；不做云端同步；不做增量/差分更新（整包替换，包体几十 MB，可接受）；不自动上传任何账号数据。

## 3. 数据层设计

### 3.1 游戏模型（`win/app/game.py`）

字段：`Game(id, label, pkg, sub, file)`

- `GAMES = (GAME_HOUSAMO, GAME_LIVEAHERO)`，`game_by_id(id)` 未知 id 回落东京放课后（与安卓 `gameById` 一致）。
- 派生：`ext_dir()` = `/sdcard/Android/data/<pkg>/<sub>`；`ext_key()` = `<ext_dir>/<file>`；`prefs()` = `/data/data/<pkg>/shared_prefs/<pkg>.v2.playerprefs.xml`；`export_sub()` = `label`。
- 东放：`files/Data/AuthKey`；LiveAHero：`files/datas/userKey`。
- `extract` / `import_key` / `backup_current` / `game_installed` 统一多一个 `game` 参数（默认东放，老调用不炸）；`EXT_CANDIDATES` 由 game 派生；`looks_like_key` 直接复用。

### 3.2 账号库：每游戏一个文件

- 路径：`%APPDATA%\HousamoAuthKeyManager\vault.<game.id>.dat`。
- 迁移：首次启动若存在旧 `vault.dat` 且不存在 `vault.housamo.dat`，`os.replace` 改名；LiveAHero 库不存在视为空库。
- `Vault` 新增 `kind` 字段：`"account"`（默认）/ `"backup"`；`load()` 对缺字段的老条目补 `kind="account"`，就地迁移。
- `add(..., kind="account")`；新增 `by_kind(kind)`。
- 去重仍按 `sha256`，但只在同一游戏文件内去重（跨游戏同一 key 允许各存一份）。

### 3.3 明文备份格式（`.hak`）

- payload 升到 `version: 2` 并带 `game`；读取 v1（无 game）按当前选中游戏入库。
- 导出文件名保持 `<账号名>.hak`，内容带游戏标识；导入界面临时提示「将导入到 <当前游戏>」。

### 3.4 设置（`win/app/config.py`）

新增键（均有默认值，老 `settings.json` 直接可用）：`active_game`（"housamo"）、`update_source`（"auto"：auto|github|mirror）、`reconcile_ignored`（{game_id: [sha256,...]}）、`last_update_check`（unix 秒）。

导出目录规则：`<save_dir>/<游戏 label>/<账号名>/AuthKey.txt`；旧文件不迁移，保持原路径可读。

## 4. 界面

### 4.1 任务页

- 设备卡标题行右侧加「游戏」分段（东京放课后 / LiveAHero 两个胶囊）；切换即写 `active_game` 并刷新账号下拉、启动核对条、按钮文案（「提取 LiveAHero 的 key」）。
- 提取/导入/打开游戏按当前游戏走，日志写明游戏名；空状态文案带游戏名。

### 4.2 账号库页

- 数量 chip 左侧加分段「账号 N / 备份 N」，只显示当前游戏、当前分段的条目。
- 备份条目可用：导入到游戏、复制 Key、显示 Key、导出 .hak、删除；不可重命名/编辑备注。
- 备份命名规则：`导入前备份 <序列号> <时间>`、`游戏内快照 <时间>`。

### 4.3 启动核对

- 时机：启动后首次设备刷新完成，或点「刷新设备」，且当前恰好一台设备在线。
- 流程：`extract(game, ...)` 只读；失败静默跳过（日志一行）。
- 判定：`sha256` 不在当前游戏库（账号 + 备份都算）→ 顶部黄色提示条「游戏里现在用的是 ab12…9f3d，账号库里没有这个 key」；按钮「存到账号库」（以「游戏内快照 <时间>」入库并导出）/「不用管」（记入 `reconcile_ignored[game]`）。
- 不阻塞操作；切换游戏时重算。

### 4.4 设置页

- 「外观 · 背景图」不动。
- 「数据与存储」补一行「当前游戏库」（vault.<id>.dat，N 个账号 · M 个备份）与「保存位置」（当前游戏子目录）。
- 新增「更新」卡：当前版本、上次检查时间、「检查更新」按钮与结果行、更新源下拉（自动/GitHub/镜像）、发现新版时「立即更新」+ 下载进度。

## 5. 更新机制（照 MAA 的形态，按 Windows 重做）

### 5.1 检查

- 启动 3 秒后后台请求 `https://api.github.com/repos/fenghuo6183/HousamoAuthKeyManager/releases/latest`（与安卓同源），`tag_name` 去 `v` 前缀与 `APP_VERSION` 逐段比较。
- 网络错误只写日志不弹窗；发现新版才提示。同一进程内只查一次，手动检查强制重查。

### 5.2 下载

- 目标：`%TEMP%\HousamoAuthKeyManager-update\AuthKeyManager-win64.zip`。
- 资产选择：优先 `AuthKeyManager-win64.zip`，否则第一个 `.zip`。
- 校验：asset 的 `digest`（sha256:...）；没有 digest 但有 `sha256sums.txt` 则用它；都没有则 WARN 后继续。
- 重试：同源重试 2 次，再切源（github → 镜像 → 手动打开 Release 页）。
- 镜像候选：`https://gh-proxy.com/<原始 url>`、`https://ghfast.top/<原始 url>`。

### 5.3 安装（副本进程，避开 exe 自锁）

1. 主程序把整个安装目录（exe + `_internal` + `assets`）复制到 `%TEMP%\HousamoAuthKeyManager-update\stage\`。
2. 用 `stage\AuthKeyManager.exe --apply-update <zip> <安装目录> <父 PID>` 启动副本，`update_state.json` 记 `stage="applying"`，主程序退出。
3. 副本：等父进程退出 → 解压覆盖安装目录（先写 `*.new` 再 `os.replace`，单文件失败即中止并回报）→ 启动新程序 → 记 `stage="done"` → 清理 stage 与 zip。
4. 失败：保留 stage 与 `update.log`，记 `stage="failed"` 与原因，不启动新程序，下次启动提示。

不用 `.bat`：杀软对「bat 替换 exe」报警率高，副本进程可写日志、可回滚。

### 5.4 失败自修复

- 启动读 `update_state.json`：`stage="applying"` 且目标版本 ≠ 当前版本 → 提示「上次更新没有完成」+「重新更新」/「忽略」；`stage="failed"` → 显示原因与「查看日志」。
- 安装前检查安装目录可写（建临时文件再删）；不可写（如 Program Files）→ 不下载，提示手动更新并打开 Release 页。

### 5.5 单实例

- 启动用 `CreateMutexW("Global\HousamoAuthKeyManager")` 判断，已有实例则置前并退出，避免两个进程同时替换安装目录。

## 6. 失败与边界

| 场景 | 处理 |
| --- | --- |
| 设备没装 LiveAHero | 任务页提示「未检测到 LiveAHero」，提取按钮禁用（`pm list packages` 判定） |
| 无 root 且 key 在私有目录 | 沿用现有报错，日志给 root 提示 |
| 旧 `vault.dat` 被占用 | 不覆盖，提示关闭程序后重试，不再写旧文件名 |
| 同一 key 在两个游戏各存一份 | 允许（库物理隔离） |
| 更新时强杀进程 | 下次启动 `stage="applying"` → 5.4 自修复 |
| 下载中断 / 校验失败 | 删半包，换源重试，最终提示手动更新 |

## 7. 验收标准

1. `python win/main.py --selftest` → `SELFTEST OK`；`py_compile` 全绿。
2. 切换游戏后账号下拉、提示条、按钮文案随之变化；提取的条目只进对应游戏的库，两个 `vault.*.dat` 独立。
3. 导入后自动备份进「备份」分段，可从备份一键导入回游戏；账号分段不含备份条目。
4. 构造「设备 key 不在库中」：提示条出现；「存到账号库」生成「游戏内快照 <时间>」；「不用管」后同一指纹不再提示且重启后仍不提示。
5. 更新：`--selftest` 覆盖版本比较；用本地伪造 zip + 假安装目录跑一次 `--apply-update`，验证替换、重启、清理、以及坏 zip → `stage="failed"` + 日志。
6. 100/125/150/200% 四档缩放下三页零裁切（沿用 `%TEMP%\sweep2.py`）。
7. README 补双游戏/备份/启动核对/自动更新与 v1.2.0 更新日志。

## 8. 风险

- 整包替换中途失败可能留下混合版本：靠 stage 状态 + 下次启动自修复兜底，最坏情况重新下载 zip 覆盖（与 MAA 一致）。
- 复制安装目录有几十 MB 额外 IO，更新时一次性发生。
- 镜像站不可靠：只作回退，默认直连 GitHub，校验失败绝不安装。
- 企业策略/代理拦截：检查不到更新时静默，不阻塞使用。

## 9. 实施顺序（交给实施计划细化）

1. 数据层：`game.py` 抽 Game、`vault.py` 分文件 + kind + 迁移、`config.py` 新键。
2. 界面：任务页游戏切换 → 账号页分段 → 导出路径按游戏分层。
3. 启动核对提示条。
4. `updater.py`（检查/下载/校验/副本进程/状态机）+ 设置页更新卡。
5. 自检脚本、README、版本号 1.2.0、打包。
