# -*- coding: utf-8 -*-
"""Page contents for the Qt shell (tasks / vault / settings)."""

from __future__ import annotations

import os
import time
from html import escape

from PySide6.QtCore import Qt, QTimer
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPlainTextEdit, QSizePolicy, QSlider, QStackedWidget,
                               QVBoxLayout, QWidget)

from app import theme

from . import base
from .widgets import Field, GlassCard, PillButton, Segmented, SubNavButton, Toggle


def muted(pal, text, size=9.5, color="text_muted"):
    label = QLabel(text)
    label.setFont(base.font(size))
    label.setStyleSheet("background: transparent; color: %s;" % pal[color])
    return label


def heading(pal, text, size=13):
    label = QLabel(text)
    label.setFont(base.font(size, bold=True))
    label.setStyleSheet("background: transparent; color: %s;" % pal["text"])
    return label


def card(shell, spacing=12):
    panel = GlassCard(shell.pal, alpha=base.card_alpha(shell.settings.get("glass")))
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(26, 22, 26, 22)
    layout.setSpacing(spacing)
    shell.register_card(panel)
    return panel, layout


def input_style(pal):
    return (
        "QLineEdit, QComboBox { background: rgba(255,255,255,0.55); border: 1px solid %s;"
        " border-radius: 9px; padding: 6px 10px; color: %s; }"
        "QLineEdit:focus, QComboBox:focus { border: 1px solid %s; }"
        "QComboBox::drop-down { border: none; width: 22px; }"
        "QComboBox QAbstractItemView { background: %s; color: %s; border: 1px solid %s;"
        " selection-background-color: %s; }"
    ) % (pal["border"], pal["text"], pal["accent"], pal["card"], pal["text"],
         pal["border"], pal["accent_soft"])


def line(pal, text=""):
    edit = QLineEdit(text)
    edit.setFont(base.font(10))
    edit.setFixedHeight(34)
    edit.setStyleSheet(input_style(pal))
    return edit


def combo(pal, items, index=0, width=260):
    box = QComboBox()
    box.addItems(items)
    box.setCurrentIndex(index)
    box.setFont(base.font(10))
    box.setFixedHeight(34)
    box.setFixedWidth(width)
    box.setStyleSheet(input_style(pal))
    return box


def _status_dot(pal, color_key="ok"):
    dot = QLabel()
    dot.setFixedSize(8, 8)
    dot.setStyleSheet("background: %s; border-radius: 4px;" % pal[color_key])
    return dot


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

GAME_LABELS = {"housamo": "Housamo", "liveahero": "LiveAHero"}


def vault_page(shell):
    from .window import Page

    page = Page(shell.pal, "账号库", "本机保存的 AuthKey 备份")
    pal = shell.pal
    ctrl = getattr(shell, "controller", None)

    panel, col = card(shell)
    head = QWidget()
    head_row = QHBoxLayout(head)
    head_row.setContentsMargins(0, 0, 0, 0)
    head_row.setSpacing(10)
    head_row.addWidget(heading(pal, "全部账号"))
    count = muted(pal, "", 9.5, "text_faint")
    head_row.addWidget(count)
    game_label = muted(pal, "", 9.5, "text_faint")
    head_row.addWidget(game_label)
    head_row.addStretch(1)
    import_btn = PillButton(pal, "导入 .hak", "ghost", height=32, min_width=104)
    head_row.addWidget(import_btn)
    col.addWidget(head)

    body = QWidget()
    body.setStyleSheet("background: transparent;")
    rows_box = QVBoxLayout(body)
    rows_box.setContentsMargins(0, 0, 0, 0)
    rows_box.setSpacing(8)
    col.addWidget(body)
    page.add(panel)
    page.column.addStretch(1)

    panel._vault_rows = rows_box
    panel._vault_count = count

    def clear_rows():
        while rows_box.count():
            item = rows_box.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def empty_state():
        box = QWidget()
        box.setStyleSheet(
            "background: rgba(255,255,255,0.38); border: 1px dashed %s; border-radius: 14px;" % pal["border"]
        )
        inner = QVBoxLayout(box)
        inner.setContentsMargins(20, 22, 20, 22)
        inner.setSpacing(6)
        title = QLabel("账号库还是空的")
        title.setFont(base.font(11, bold=True))
        title.setStyleSheet("background: transparent; color: %s;" % pal["text"])
        title.setAlignment(Qt.AlignCenter)
        hint = muted(pal, "先在「任务」页连接设备做一次备份，或者点右上角导入 .hak 文件", 9.5, "text_faint")
        hint.setAlignment(Qt.AlignCenter)
        inner.addWidget(title)
        inner.addWidget(hint)
        rows_box.addWidget(box)

    def export_row(entry, button):
        default = "%s_%s.hak" % (entry.get("name") or "housamo",
                                 time.strftime("%Y%m%d_%H%M"))
        path, _ = QFileDialog.getSaveFileName(panel, "导出 AuthKey", default,
                                              "AuthKey 文件 (*.hak)")
        if path and ctrl is not None:
            ctrl.export_entry(entry.get("id"), path)

    def delete_row(entry, button):
        if button.property("armed"):
            if ctrl is not None:
                ctrl.delete_entry(entry.get("id"))
            return
        button.property("timer")
        button.setProperty("armed", True)
        button.setText("再点一次")
        timer = QTimer(button)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda: (button.setProperty("armed", False), button.setText("删除")))
        timer.start(3000)
        button._vault_timer = timer

    def make_row(entry):
        row = QWidget()
        row.setObjectName("vaultRow")
        row.setStyleSheet(
            "QWidget#vaultRow { background: rgba(255,255,255,0.5); border-radius: 12px; }"
        )
        box = QHBoxLayout(row)
        box.setContentsMargins(14, 10, 12, 10)
        box.setSpacing(12)

        chip = QLabel(GAME_LABELS.get(entry.get("game"), "Housamo"))
        chip.setFont(base.font(8.5, bold=True))
        chip.setStyleSheet(
            "background: %s; color: %s; border-radius: 8px; padding: 2px 8px;" % (pal["accent_soft"], pal["accent"])
        )
        box.addWidget(chip)

        name = QLabel(entry.get("name") or "未命名账号")
        name.setFont(base.font(10.5, bold=True))
        name.setStyleSheet("background: transparent; color: %s;" % pal["text"])
        box.addWidget(name)

        fp = QLabel(entry.get("fingerprint") or "")
        fp.setFont(base.mono(8.5))
        fp.setStyleSheet("background: transparent; color: %s;" % pal["text_faint"])
        box.addWidget(fp)
        box.addStretch(1)

        when = muted(pal, (entry.get("created_at") or "")[:16], 9, "text_faint")
        box.addWidget(when)

        export_btn = PillButton(pal, "导出", "ghost", height=28, min_width=64)
        export_btn.clicked.connect(lambda _=False, e=entry, b=export_btn: export_row(e, b))
        box.addWidget(export_btn)

        delete_btn = PillButton(pal, "删除", "danger", height=28, min_width=64)
        delete_btn.clicked.connect(lambda _=False, e=entry, b=delete_btn: delete_row(e, b))
        box.addWidget(delete_btn)
        return row

    def rebuild(entries):
        clear_rows()
        entries = list(entries or [])
        count.setText("%d 条" % len(entries) if entries else "")
        if not entries:
            empty_state()
            return
        for entry in entries:
            rows_box.addWidget(make_row(entry))

    def do_import():
        path, _ = QFileDialog.getOpenFileName(panel, "导入 AuthKey", "", "AuthKey 文件 (*.hak);;所有文件 (*)")
        if path and ctrl is not None:
            ctrl.import_file(path)

    import_btn.clicked.connect(lambda _=False: do_import())

    def show_game(game):
        game_label.setText("·  当前 %s" % GAME_LABELS.get(getattr(game, "id", ""), "Housamo"))

    if ctrl is not None:
        ctrl.vault_changed.connect(rebuild)
        ctrl.game_changed.connect(show_game)
        if ctrl.service is not None:
            show_game(ctrl.service.game)
            rebuild(ctrl.service.vault.entries)
        else:
            rebuild([])
    else:
        rebuild([
            {"id": "a", "name": "主账号", "game": "housamo", "fingerprint": "4F2A-91C7",
             "created_at": "2026-11-28 12:04:00"},
            {"id": "b", "name": "小号", "game": "housamo", "fingerprint": "B81D-30E5",
             "created_at": "2026-11-21 20:31:00"},
            {"id": "c", "name": "主账号", "game": "liveahero", "fingerprint": "77CE-0A42",
             "created_at": "2026-11-19 09:12:00"},
        ])
    return page


CONNECT_PROFILES = (
    ("自动检测", "auto", ""),
    ("MuMu 模拟器", "mumu", "16384"),
    ("雷电模拟器", "ld", "5555"),
    ("夜神模拟器", "nox", "62001"),
    ("BlueStacks", "bst", "5555"),
    ("自定义", "custom", None),
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
    col.addWidget(Field(pal, "当前游戏", game_seg, "账号库、备份和导出都跟着这个游戏"))

    profile_keys = [item[1] for item in CONNECT_PROFILES]
    profile_names = [item[0] for item in CONNECT_PROFILES]
    profile = settings.get("connect_profile") or "auto"
    profile_box = combo(pal, profile_names,
                        profile_keys.index(profile) if profile in profile_keys else 0, width=220)
    ports_edit = line(pal, settings.get("emulator_ports") or "")
    ports_edit.setMinimumWidth(240)
    ports_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    ports_edit.setCursorPosition(0)
    ports_hint = muted(pal, "", 9, "text_faint")

    def set_hint(text, color="text_faint"):
        ports_hint.setText(text)
        ports_hint.setStyleSheet("background: transparent; color: %s;" % pal[color])

    def apply_profile(index):
        key = CONNECT_PROFILES[index][1]
        ports = CONNECT_PROFILES[index][2]
        settings.set("connect_profile", key)
        if ports:
            ports_edit.setText(ports)
            settings.set("emulator_ports", ports)
            set_hint("这个配置只试 %s" % ports)
        elif ports == "":
            from app.config import EMULATOR_PORTS
            text = ",".join(str(p) for p in EMULATOR_PORTS)
            ports_edit.setText(text)
            settings.set("emulator_ports", text)
            set_hint("自动检测会按顺序试 %d 个常见端口" % len(EMULATOR_PORTS))
        else:
            set_hint("自定义：自己填端口，改完按回车保存")

    profile_box.currentIndexChanged.connect(apply_profile)
    col.addWidget(Field(pal, "连接配置", profile_box, "选模拟器品牌，或自己填端口"))

    def commit_ports():
        from .service import parse_ports
        try:
            ports = parse_ports(ports_edit.text())
        except Exception as exc:
            set_hint(str(exc), "err")
            return
        text = ",".join(str(port) for port in ports)
        settings.set("emulator_ports", text)
        ports_edit.setText(text)
        set_hint("当前 %d 个端口" % len(ports), "text_muted")

    ports_edit.editingFinished.connect(commit_ports)
    col.addWidget(Field(pal, "扫描端口", ports_edit, "逗号或分号分隔，回车保存", expand=True))

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
    col.addWidget(Field(pal, "启动时自动连接", auto, "记住的设备可用时直接连上"))

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


def _look_section(shell, page):
    pal = shell.pal
    settings = shell.settings

    panel, col = card(shell)
    col.addWidget(heading(pal, "外观"))
    glass_slider = _slider(pal, settings.get("glass") or 0)
    readout = muted(pal, "%d%%" % glass_slider.value(), 10, "text")
    glass_row = QWidget()
    glass_box = QHBoxLayout(glass_row)
    glass_box.setContentsMargins(0, 0, 0, 0)
    glass_box.setSpacing(12)
    glass_box.addWidget(glass_slider)
    glass_box.addWidget(readout)
    glass_box.addStretch(1)

    def on_glass(value):
        readout.setText("%d%%" % value)
        shell.set_glass(value)
        settings.set("glass", value, save=False)

    def commit_glass():
        settings.set("glass", glass_slider.value())

    glass_slider.valueChanged.connect(on_glass)
    glass_slider.sliderReleased.connect(commit_glass)
    col.addWidget(Field(pal, "卡片透明度", glass_row, "越大卡片越透，底下壁纸越明显"))

    theme_seg = Segmented(pal, ["浅色", "深色"], 0 if settings.get("theme") != "dark" else 1, width=200)

    def on_theme(index):
        settings.set("theme", "dark" if index else "light")

    theme_seg.changed.connect(on_theme)
    col.addWidget(Field(pal, "主题", theme_seg, "切换后重启程序生效"))

    blur_slider = _slider(pal, settings.get("bg_blur") or 0, 0, 40, width=200)
    blur_readout = muted(pal, "%d" % blur_slider.value(), 10, "text")
    blur_row = QWidget()
    blur_box = QHBoxLayout(blur_row)
    blur_box.setContentsMargins(0, 0, 0, 0)
    blur_box.setSpacing(12)
    blur_box.addWidget(blur_slider)
    blur_box.addWidget(blur_readout)
    blur_box.addStretch(1)

    def on_blur(value):
        blur_readout.setText("%d" % value)

    def commit_blur():
        shell.set_backdrop(blur=blur_slider.value())

    blur_slider.valueChanged.connect(on_blur)
    blur_slider.sliderReleased.connect(commit_blur)
    col.addWidget(Field(pal, "壁纸模糊", blur_row, "0 = 不模糊，越大越柔"))

    bg_name = muted(pal, os.path.basename(settings.get("bg_image") or "") or "还没选壁纸",
                    9.5, "text_muted")
    pick = PillButton(pal, "选择壁纸", "ghost", height=32, min_width=96)
    reset = PillButton(pal, "恢复默认", "ghost", height=32, min_width=96)
    bg_row = QWidget()
    bg_box = QHBoxLayout(bg_row)
    bg_box.setContentsMargins(0, 0, 0, 0)
    bg_box.setSpacing(10)
    bg_box.addWidget(bg_name)
    bg_box.addWidget(pick)
    bg_box.addWidget(reset)

    def do_pick():
        from app import config as config_mod
        path, _ = QFileDialog.getOpenFileName(
            panel, "选择壁纸", "", "图片 (*.png *.jpg *.jpeg *.bmp *.webp);;所有文件 (*)")
        if not path:
            return
        try:
            stored = config_mod.store_background(path)
        except Exception as exc:
            if shell.controller is not None:
                shell.controller.log("失败", "壁纸没换成：%s" % exc)
            return
        settings.set("bg_image", stored)
        shell.set_backdrop(path=stored)
        bg_name.setText(os.path.basename(stored))

    def do_reset():
        from app import config as config_mod
        config_mod.clear_background()
        settings.set("bg_image", "")
        shell.set_backdrop(path="")
        bg_name.setText("还没选壁纸")

    pick.clicked.connect(lambda _=False: do_pick())
    reset.clicked.connect(lambda _=False: do_reset())
    col.addWidget(Field(pal, "背景壁纸", bg_row, "图片会复制到程序目录，动原图也没关系"))
    page.add(panel)


def _update_section(shell, page):
    pal = shell.pal
    ctrl = getattr(shell, "controller", None)
    settings = shell.settings

    panel, col = card(shell)
    col.addWidget(heading(pal, "更新"))
    check_toggle = Toggle(pal, bool(settings.get("auto_check_update")))

    def on_auto_check(checked):
        settings.set("auto_check_update", bool(checked))

    check_toggle.toggled.connect(on_auto_check)
    col.addWidget(Field(pal, "自动检查更新", check_toggle, "启动时检查一次"))

    check_btn = PillButton(pal, "立即检查", "ghost", height=36, min_width=104)
    version = muted(pal, "当前版本 %s" % theme.APP_VERSION, 9.5, "text_faint")
    update_row = QWidget()
    update_box = QHBoxLayout(update_row)
    update_box.setContentsMargins(0, 0, 0, 0)
    update_box.setSpacing(12)
    update_box.addWidget(check_btn)
    update_box.addWidget(version)
    update_box.addStretch(1)
    check_btn.clicked.connect(lambda _=False: ctrl.check_update() if ctrl is not None else None)
    col.addWidget(update_row)
    page.add(panel)


def _data_section(shell, page):
    pal = shell.pal
    ctrl = getattr(shell, "controller", None)

    panel, col = card(shell)
    col.addWidget(heading(pal, "数据与存储"))
    from app import config as config_mod
    folder = line(pal, config_mod.app_dir())
    folder.setReadOnly(True)
    folder.setMinimumWidth(220)
    folder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    folder.setCursorPosition(0)
    col.addWidget(Field(pal, "保存目录", folder, "账号库、壁纸和设置都放在这里", expand=True))

    open_dir = PillButton(pal, "打开目录", "ghost", height=34, min_width=96)
    open_log = PillButton(pal, "更新日志", "ghost", height=34, min_width=96)

    def do_open(path):
        try:
            os.startfile(path)
        except Exception as exc:
            if ctrl is not None:
                ctrl.log("失败", "打不开目录：%s" % exc)

    open_dir.clicked.connect(lambda _=False: do_open(config_mod.app_dir()))
    open_log.clicked.connect(lambda _=False: do_open(os.path.join(config_mod.app_dir(), "update.log")))
    data_row = QWidget()
    data_box = QHBoxLayout(data_row)
    data_box.setContentsMargins(0, 0, 0, 0)
    data_box.setSpacing(10)
    data_box.addWidget(open_dir)
    data_box.addWidget(open_log)
    data_box.addStretch(1)
    col.addWidget(data_row)
    page.add(panel)


def _about_section(shell, page):
    pal = shell.pal

    panel, col = card(shell)
    col.addWidget(heading(pal, "关于"))
    col.addWidget(Field(pal, "版本", muted(pal, "v" + theme.APP_VERSION, 10, "text"),
                        "开源项目，反馈和更新都在项目主页"))
    home = PillButton(pal, "项目主页", "ghost", height=34, min_width=104)

    def do_home():
        try:
            os.startfile(theme.REPO_URL)
        except Exception:
            pass

    home.clicked.connect(lambda _=False: do_home())
    row = QWidget()
    box = QHBoxLayout(row)
    box.setContentsMargins(0, 0, 0, 0)
    box.setSpacing(10)
    box.addWidget(home)
    box.addStretch(1)
    col.addWidget(row)
    page.add(panel)


class _NavPanel(QWidget):
    """Translucent rounded panel behind the settings sub-navigation."""

    def __init__(self, pal, parent=None):
        super().__init__(parent)
        self.pal = pal
        self.setFixedWidth(236)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy().Fixed,
                           self.sizePolicy().verticalPolicy().Maximum)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(18, 18, -8, -18)
        p.setPen(QPen(base.qc(self.pal["border"], 110), 1))
        p.setBrush(base.qc(self.pal["card"], 128))
        p.drawRoundedRect(rect, 22, 22)


class _SettingsPage(QWidget):
    """Settings with a MAA-style sub-navigation on the left."""

    def __init__(self, shell, pal):
        from .window import Page

        super().__init__()
        self.setStyleSheet("background: transparent;")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        nav = _NavPanel(pal, self)
        nav_col = QVBoxLayout(nav)
        nav_col.setContentsMargins(40, 42, 26, 42)
        nav_col.setSpacing(6)
        title = QLabel("设置")
        title.setFont(base.font(19, bold=True))
        title.setStyleSheet("background: transparent; color: %s;" % pal["text"])
        nav_col.addWidget(title)
        nav_col.addSpacing(20)

        self.stack = QStackedWidget(self)
        self.buttons = []
        sections = (
            ("connect", "连接设置", "连接设置", "设备、端口和记住的设备", _connect_section),
            ("look", "外观设置", "外观设置", "壁纸、透明度和主题", _look_section),
            ("update", "更新设置", "更新设置", "检查新版本", _update_section),
            ("data", "数据与存储", "数据与存储", "账号库和日志放在哪里", _data_section),
            ("about", "关于我们", "关于我们", "版本与项目主页", _about_section),
        )
        for index, (key, label, page_title, subtitle, builder) in enumerate(sections):
            button = SubNavButton(pal, label, nav)
            button.clicked.connect(lambda _=False, i=index: self.select(i))
            nav_col.addWidget(button)
            self.buttons.append(button)
            page = Page(pal, page_title, subtitle)
            page.column.setContentsMargins(24, 26, 30, 26)
            builder(shell, page)
            page.column.addStretch(1)
            self.stack.addWidget(page)
        nav_col.addStretch(1)
        row.addWidget(nav, 0, Qt.AlignTop)
        row.addWidget(self.stack, 1)
        self.select(0)

    def select(self, index):
        self.stack.setCurrentIndex(index)
        for position, button in enumerate(self.buttons):
            button.setChecked(position == index)
            button.update()


def settings_page(shell):
    return _SettingsPage(shell, shell.pal)
