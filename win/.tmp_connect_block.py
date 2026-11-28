CONNECT_PROFILES = (
    ("自动检测", "auto", "", ""),
    ("MuMu 模拟器", "mumu", "16384", "127.0.0.1:16384"),
    ("雷电模拟器", "ld", "5555", "127.0.0.1:5555"),
    ("夜神模拟器", "nox", "62001", "127.0.0.1:62001"),
    ("BlueStacks", "bst", "5555", "127.0.0.1:5555"),
    ("自定义", "custom", None, None),
)


def _slider(pal, value, low=0, high=100, width=260):
    bar = QSlider(Qt.Horizontal)
    bar.setRange(low, high)
    bar.setValue(int(value))
    bar.setFixedWidth(width)
    bar.setStyleSheet(
        "QSlider::groove:horizontal{height:6px;border-radius:3px;background:%s;}"
        "QSlider::sub-page:horizontal{background:%s;border-radius:3px;}"
        "QSlider::handle:horizontal{width:16px;height:16px;margin:-5px 0;border-radius:8px;"
        "background:#FFFFFF;border:1px solid %s;}"
        % (pal["card_soft"], pal["accent"], pal["accent"])
    )
    return bar


def _connect_section(shell, page):
    pal = shell.pal
    ctrl = getattr(shell, "controller", None)
    settings = shell.settings

    panel, col = card(shell)
    col.addWidget(heading(pal, "连接"))

    game_ids = ["housamo", "liveahero"]
    game_names = ["Housamo", "LiveAHero"]
    current = game_ids.index(settings.get("active_game")) if settings.get("active_game") in game_ids else 0
    game_seg = Segmented(pal, game_names, current, width=240)

    def on_game(index):
        if ctrl is not None:
            ctrl.switch_game(game_ids[index])
        else:
            settings.set("active_game", game_ids[index])

    game_seg.changed.connect(on_game)
    col.addWidget(Field(pal, "当前游戏", game_seg, "账号库和导出跟着它"))

    # ---- 连接配置：选品牌会同时填好端口和地址（和 MAA 一样）
    profile_keys = [item[1] for item in CONNECT_PROFILES]
    profile_names = [item[0] for item in CONNECT_PROFILES]
    profile = settings.get("connect_profile") or "auto"
    profile_box = combo(pal, profile_names,
                        profile_keys.index(profile) if profile in profile_keys else 0, width=320)
    profile_box.setMinimumWidth(220)
    profile_box.setMaximumWidth(16777215)
    profile_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    # ---- 连接地址：可直接输入，也可以从下拉里挑已连接的设备
    addr_combo = QComboBox()
    addr_combo.setFont(base.font(10))
    addr_combo.setFixedHeight(34)
    addr_combo.setEditable(True)
    addr_combo.setInsertPolicy(QComboBox.NoInsert)
    addr_combo.setStyleSheet(input_style(pal))
    addr_combo.setMinimumWidth(200)
    addr_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    addr_combo.setCurrentText(settings.get("preferred_serial") or "")
    addr = addr_combo.lineEdit()
    addr.setPlaceholderText("127.0.0.1:16384，也可以只填端口")

    ports_edit = line(pal, settings.get("emulator_ports") or "")
    ports_edit.setMinimumWidth(240)
    ports_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    ports_edit.setCursorPosition(0)

    def note(text):
        if ctrl is not None:
            ctrl.log("设置", text)

    def apply_profile(index):
        key, ports, address = CONNECT_PROFILES[index][1:]
        settings.set("connect_profile", key)
        if ports is None:
            note("已切到自定义配置：自己填端口和地址")
            return
        if ports == "":
            from app.config import EMULATOR_PORTS
            text = ",".join(str(port) for port in EMULATOR_PORTS)
            ports_edit.setText(text)
            settings.set("emulator_ports", text)
            note("自动检测会按顺序试 %d 个常见端口" % len(EMULATOR_PORTS))
        else:
            ports_edit.setText(ports)
            settings.set("emulator_ports", ports)
            note("已切到 %s：只扫端口 %s" % (CONNECT_PROFILES[index][0], ports))
        if address:
            addr_combo.setCurrentText(address)
            settings.set("preferred_serial", address)
        elif address == "":
            addr_combo.setCurrentText("")
            settings.set("preferred_serial", "")

    profile_box.currentIndexChanged.connect(apply_profile)
    col.addWidget(Field(pal, "连接配置", profile_box, "选品牌会自动填好端口和地址"))

    def normalized_address():
        from app.adb import normalize_address
        return normalize_address(addr.text())

    def remember_address():
        serial = normalized_address()
        if not serial:
            return ""
        addr_combo.setCurrentText(serial)
        addr.setCursorPosition(0)
        settings.set("preferred_serial", serial)
        return serial

    addr.editingFinished.connect(remember_address)

    get_btn = PillButton(pal, "获取设备", "ghost", height=32, min_width=88)
    test_btn = PillButton(pal, "连接测试", "ghost", height=32, min_width=88)
    link_btn = PillButton(pal, "连接", "soft", height=32, min_width=72)

    addr_input = QWidget()
    addr_input_box = QHBoxLayout(addr_input)
    addr_input_box.setContentsMargins(0, 0, 0, 0)
    addr_input_box.setSpacing(8)
    addr_input_box.addWidget(addr_combo, 1)
    addr_input_box.addWidget(get_btn)

    addr_actions = QWidget()
    addr_actions_box = QHBoxLayout(addr_actions)
    addr_actions_box.setContentsMargins(0, 0, 0, 0)
    addr_actions_box.setSpacing(8)
    addr_actions_box.addWidget(test_btn)
    addr_actions_box.addWidget(link_btn)
    addr_actions_box.addStretch(1)

    addr_row = QWidget()
    addr_box = QVBoxLayout(addr_row)
    addr_box.setContentsMargins(0, 0, 0, 0)
    addr_box.setSpacing(8)
    addr_box.addWidget(addr_input)
    addr_box.addWidget(addr_actions)

    def fill_from_devices():
        service = getattr(ctrl, "service", None) if ctrl is not None else None
        if service is None:
            return
        online = [dev for dev in service.devices if dev.online]
        if online:
            addr_combo.blockSignals(True)
            addr_combo.clear()
            addr_combo.addItems([dev.serial for dev in online])
            addr_combo.setCurrentText(online[0].serial)
            addr_combo.blockSignals(False)
            remember_address()
        elif ctrl is not None:
            ctrl.log("提示", "没找到在线设备，先打开模拟器再点「获取设备」")

    def do_get_device():
        if ctrl is None:
            return
        ctrl.refresh_devices()
        QTimer.singleShot(1500, fill_from_devices)

    def do_test():
        if ctrl is not None:
            ctrl.test_connection(normalized_address())

    def do_link():
        serial = remember_address()
        if ctrl is not None:
            ctrl.connect(serial)

    get_btn.clicked.connect(lambda _=False: do_get_device())
    test_btn.clicked.connect(lambda _=False: do_test())
    link_btn.clicked.connect(lambda _=False: do_link())
    col.addWidget(Field(pal, "连接地址", addr_row, "也可以只填端口，回车记住"))

    # ---- ADB 路径：和 MAA 一样显示完整路径 + 选择
    adb_path = settings.get("adb_path") or ""
    adb_edit = line(pal, adb_path or "自动（内置 platform-tools）")
    adb_edit.setReadOnly(True)
    adb_edit.setCursorPosition(0)
    adb_edit.setToolTip(adb_path or "程序会优先用自带的 platform-tools")
    pick_adb = PillButton(pal, "选择", "ghost", height=30, min_width=68)
    reset_adb = PillButton(pal, "默认", "ghost", height=30, min_width=68)
    adb_row = QWidget()
    adb_box = QHBoxLayout(adb_row)
    adb_box.setContentsMargins(0, 0, 0, 0)
    adb_box.setSpacing(8)
    adb_box.addWidget(adb_edit, 1)
    adb_box.addWidget(pick_adb)
    adb_box.addWidget(reset_adb)

    def do_pick_adb():
        path, _ = QFileDialog.getOpenFileName(
            panel, "选择 adb.exe", "", "adb.exe (adb.exe);;所有文件 (*)")
        if not path:
            return
        settings.set("adb_path", path)
        adb_edit.setText(path)
        adb_edit.setCursorPosition(0)
        adb_edit.setToolTip(path)
        if ctrl is not None:
            ctrl.log("设置", "adb 路径已改，重启程序后生效")

    def do_reset_adb():
        settings.set("adb_path", "")
        adb_edit.setText("自动（内置 platform-tools）")
        adb_edit.setCursorPosition(0)
        adb_edit.setToolTip("")
        if ctrl is not None:
            ctrl.log("设置", "adb 路径恢复自动，重启程序后生效")

    pick_adb.clicked.connect(lambda _=False: do_pick_adb())
    reset_adb.clicked.connect(lambda _=False: do_reset_adb())
    col.addWidget(Field(pal, "ADB 路径", adb_row, "找不到设备时换一个", expand=True))

    def commit_ports():
        from .service import parse_ports
        try:
            ports = parse_ports(ports_edit.text())
        except Exception as exc:
            note("端口填错了：%s" % exc)
            return
        text = ",".join(str(port) for port in ports)
        settings.set("emulator_ports", text)
        ports_edit.setText(text)
        note("扫描端口已保存：%d 个" % len(ports))

    ports_edit.editingFinished.connect(commit_ports)
    col.addWidget(Field(pal, "扫描端口", ports_edit, "自动检测时按这些端口找设备", expand=True))

    only = Toggle(pal, bool(settings.get("only_emulators")))

    def on_only(checked):
        settings.set("only_emulators", bool(checked))
        if ctrl is not None:
            ctrl.refresh_devices()

    only.toggled.connect(on_only)
    col.addWidget(Field(pal, "只显示模拟器", only, "隐藏真机设备"))

    auto = Toggle(pal, bool(settings.get("auto_connect")))

    def on_auto(checked):
        settings.set("auto_connect", bool(checked))

    auto.toggled.connect(on_auto)
    col.addWidget(Field(pal, "启动时自动连接", auto, "记住的设备直接连上"))

    reconnect = Toggle(pal, bool(settings.get("auto_reconnect")))

    def on_reconnect(checked):
        settings.set("auto_reconnect", bool(checked))

    reconnect.toggled.connect(on_reconnect)
    col.addWidget(Field(pal, "自动重连", reconnect, "掉线后自动再试一次"))

    remembered = muted(pal, settings.get("preferred_serial") or "还没有记住的设备", 9.5, "text_muted")
    forget = PillButton(pal, "忘记", "ghost", height=30, min_width=72)
    dev_row = QWidget()
    dev_box = QHBoxLayout(dev_row)
    dev_box.setContentsMargins(0, 0, 0, 0)
    dev_box.setSpacing(10)
    dev_box.addWidget(remembered)
    dev_box.addWidget(forget)

    def do_forget():
        settings.set("preferred_serial", "")
        if ctrl is not None and ctrl.service is not None:
            ctrl.service.serial = ""
        remembered.setText("还没有记住的设备")

    forget.clicked.connect(lambda _=False: do_forget())
    col.addWidget(Field(pal, "记住的设备", dev_row, "连接成功后自动记住"))
    page.add(panel)
