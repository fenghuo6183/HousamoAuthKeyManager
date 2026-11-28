def tasks_page(shell):
    from .window import Page

    page = Page(shell.pal, "任务", "连接设备、备份与恢复 AuthKey")
    pal = shell.pal
    ctrl = getattr(shell, "controller", None)

    # ---- 连接
    panel, col = card(shell)
    col.addWidget(heading(pal, "连接"))

    status = QWidget()
    status_row = QHBoxLayout(status)
    status_row.setContentsMargins(0, 0, 0, 0)
    status_row.setSpacing(9)
    dot = QLabel()
    dot.setFixedSize(8, 8)
    dot.setStyleSheet("background: %s; border-radius: 4px;" % pal["warn"])
    status_title = muted(pal, "未连接 · 正在准备 adb", 10, "text")
    status_detail = muted(pal, "", 9, "text_faint")
    status_row.addWidget(dot)
    status_row.addWidget(status_title)
    status_row.addWidget(status_detail)
    status_row.addStretch(1)
    col.addWidget(status)

    devices = combo(pal, [], 0, 340)
    devices.setEditable(True)
    devices.lineEdit().setFont(base.font(10))
    devices.lineEdit().setPlaceholderText("选择设备，或直接填 127.0.0.1:16384")
    refresh = PillButton(pal, "刷新", "ghost", height=34, min_width=88)
    holder = QWidget()
    holder_row = QHBoxLayout(holder)
    holder_row.setContentsMargins(0, 0, 0, 0)
    holder_row.setSpacing(10)
    holder_row.addWidget(devices)
    holder_row.addWidget(refresh)
    holder_row.addStretch(1)
    col.addWidget(Field(pal, "设备", holder, "在线设备优先，下拉里是 adb devices 的结果"))

    actions = QWidget()
    actions_row = QHBoxLayout(actions)
    actions_row.setContentsMargins(0, 0, 0, 0)
    actions_row.setSpacing(10)
    btn_connect = PillButton(pal, "连接", "primary", height=40, min_width=120)
    btn_scan = PillButton(pal, "扫描端口", "ghost", height=40)
    actions_row.addWidget(btn_connect)
    actions_row.addWidget(btn_scan)
    actions_row.addStretch(1)
    col.addWidget(actions)
    page.add(panel)

    # ---- 快捷操作
    panel, col = card(shell)
    col.addWidget(heading(pal, "快捷操作"))
    grid = QWidget()
    grid_row = QHBoxLayout(grid)
    grid_row.setContentsMargins(0, 0, 0, 0)
    grid_row.setSpacing(10)
    btn_open = PillButton(pal, "打开游戏", "primary", height=42)
    btn_backup = PillButton(pal, "立即备份", "soft", height=42)
    btn_import = PillButton(pal, "导入 AuthKey", "ghost", height=42)
    btn_export = PillButton(pal, "导出 AuthKey", "ghost", height=42)
    for button in (btn_open, btn_backup, btn_import, btn_export):
        grid_row.addWidget(button)
    grid_row.addStretch(1)
    col.addWidget(grid)
    hint = muted(pal, "备份写进账号库（加密保存）；导出会存成 .hak 文件，导入会把 .hak 写回游戏。", 9.5, "text_faint")
    hint.setWordWrap(True)
    col.addWidget(hint)
    page.add(panel)

    # ---- 日志
    panel, col = card(shell)
    head = QWidget()
    head_row = QHBoxLayout(head)
    head_row.setContentsMargins(0, 0, 0, 0)
    head_row.addWidget(heading(pal, "运行日志"))
    head_row.addStretch(1)
    btn_clear = PillButton(pal, "清空", "ghost", height=30, min_width=80)
    head_row.addWidget(btn_clear)
    col.addWidget(head)

    log = QPlainTextEdit()
    log.setReadOnly(True)
    log.setMaximumBlockCount(600)
    log.setFont(base.mono(9.5))
    log.setFixedHeight(168)
    log.setStyleSheet(
        "QPlainTextEdit { background: %s; color: %s; border: none; border-radius: 12px;"
        " padding: 10px 12px; selection-background-color: %s; }"
        "QScrollBar:vertical { background: transparent; width: 10px; margin: 4px 2px; }"
        "QScrollBar::handle:vertical { background: %s; border-radius: 3px; min-height: 24px; }"
        "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        % (pal["log_bg"], pal["log_fg"], pal["accent_soft"], pal["log_dim"])
    )
    col.addWidget(log)
    page.add(panel)
    page.column.addStretch(1)

    TONE = {"失败": "err", "错误": "err", "完成": "ok", "提示": "warn", "连接": "accent"}
    tag_color = {
        "err": pal["log_err"], "ok": pal["log_ok"], "warn": pal["warn"],
        "accent": pal["accent"], "dim": pal["log_dim"], "fg": pal["log_fg"],
    }

    def append(tag, message):
        stamp = time.strftime("%H:%M:%S")
        color = tag_color.get(TONE.get(tag, "dim"), pal["log_dim"])
        log.appendHtml(
            '<span style="color:%s">%s</span>&nbsp;&nbsp;'
            '<span style="color:%s">%s</span>&nbsp;&nbsp;'
            '<span style="color:%s">%s</span>'
            % (pal["log_dim"], stamp, color, escape(tag or "信息"),
               pal["log_fg"], escape(message))
        )
        bar = log.verticalScrollBar()
        bar.setValue(bar.maximum())

    btn_clear.clicked.connect(log.clear)

    # ---- 交互
    def current_serial():
        data = devices.currentData()
        if data:
            return str(data)
        text = devices.currentText().strip()
        if not text:
            return ""
        tail = text.split()[-1]
        return tail if ":" in tail or tail.startswith("emulator-") else text

    def set_state(kind, title, detail=""):
        color = pal["text_faint"] if kind == "muted" else pal.get(kind, pal["text_faint"])
        dot.setStyleSheet("background: %s; border-radius: 4px;" % color)
        status_title.setText(title)
        status_detail.setText(("  ·  " + detail) if detail else "")

    def on_devices(devs):
        only = bool(shell.settings.get("only_emulators"))
        visible = [d for d in devs if d.online and (not only or d.is_emulator)]
        keep = current_serial()
        devices.blockSignals(True)
        devices.clear()
        for dev in visible:
            devices.addItem("%s  ·  %s" % (dev.short_label, dev.serial), dev.serial)
        if keep:
            for i in range(devices.count()):
                if devices.itemData(i) == keep:
                    devices.setCurrentIndex(i)
                    break
        elif devices.count():
            devices.setCurrentIndex(0)
        devices.blockSignals(False)
        if not visible and not keep:
            devices.setEditText("")

    def on_busy(busy):
        for button in (btn_connect, btn_scan, refresh, btn_open, btn_backup,
                       btn_import, btn_export):
            button.setEnabled(not busy)

    btn_connect.clicked.connect(lambda: ctrl and ctrl.connect(current_serial()))
    btn_scan.clicked.connect(lambda: ctrl and ctrl.scan_ports())
    refresh.clicked.connect(lambda: ctrl and ctrl.refresh_devices())
    btn_open.clicked.connect(lambda: ctrl and ctrl.launch_game())
    btn_backup.clicked.connect(lambda: ctrl and ctrl.backup())

    def do_export():
        if not ctrl:
            return
        guess = "%s_%s.hak" % (shell.settings.get("active_game") or "housamo",
                               time.strftime("%Y%m%d_%H%M"))
        path, _ = QFileDialog.getSaveFileName(page, "导出 AuthKey", guess, "AuthKey 备份 (*.hak)")
        if path:
            ctrl.export_current(path)

    def do_import():
        if not ctrl:
            return
        path, _ = QFileDialog.getOpenFileName(page, "导入 AuthKey", "", "AuthKey 备份 (*.hak)")
        if path:
            ctrl.import_to_device(path)

    btn_export.clicked.connect(do_export)
    btn_import.clicked.connect(do_import)

    if ctrl:
        ctrl.logged.connect(append)
        ctrl.devices_ready.connect(on_devices)
        ctrl.state_changed.connect(set_state)
        ctrl.busy_changed.connect(on_busy)
        ctrl.game_changed.connect(lambda game: set_state("muted", "已切换到 %s" % game.label))
        ctrl.log("提示", "客户端已就绪，等 adb 扫描设备")
    else:
        for button in (btn_connect, btn_scan, refresh, btn_open, btn_backup,
                       btn_import, btn_export, btn_clear):
            button.setEnabled(False)
        devices.addItems(["MuMu 模拟器  ·  127.0.0.1:16384", "雷电模拟器  ·  127.0.0.1:7555"])
        for tag, text in (
            ("设备", "发现 2 台设备"),
            ("连接", "已连接 127.0.0.1:16384（MuMu 模拟器）"),
            ("备份", "已从外部存储读取到东京放课后的 key"),
            ("完成", "已备份：备份 11-28 12:04"),
        ):
            append(tag, text)
    return page
