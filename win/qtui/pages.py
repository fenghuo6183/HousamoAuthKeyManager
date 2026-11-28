# -*- coding: utf-8 -*-
"""Page contents for the Qt shell (tasks / vault / settings)."""

from __future__ import annotations

import os
import time
from html import escape

from PySide6.QtCore import Qt, QTimer
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPlainTextEdit, QSizePolicy, QSlider, QStackedWidget,
                               QVBoxLayout, QWidget)

from app import theme

from . import base, dialogs
from .widgets import (ChevronCombo, Field, GlassCard, PillButton, Segmented,
                      SubNavButton, Toggle)


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


def card(shell, spacing=12, head=None):
    panel = GlassCard(shell.pal, alpha=base.card_alpha(shell.settings.get("glass")), shadow=False)
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(26, 22, 26, 22)
    layout.setSpacing(spacing)
    if head is not None:
        layout.addWidget(head)
        layout.addSpacing(6)
    shell.register_card(panel)
    return panel, layout


def input_style(pal):
    return (
        "QLineEdit, QComboBox { background: rgba(255,255,255,0.55); border: 1px solid %s;"
        " border-radius: 9px; padding: 6px 10px; color: %s; }"
        "QLineEdit:focus, QComboBox:focus { border: 1px solid %s; }"
        "QComboBox::drop-down { border: none; width: 22px; }"
        "QComboBox QLineEdit { background: transparent; border: none; padding: 0px; color: %s; }"
        "QComboBox QAbstractItemView { background: %s; color: %s; border: 1px solid %s;"
        " selection-background-color: %s; }"
    ) % (pal["border"], pal["text"], pal["accent"], pal["text"], pal["card"], pal["text"],
         pal["border"], pal["accent_soft"])


def line(pal, text=""):
    edit = QLineEdit(text)
    edit.setFont(base.font(10))
    edit.setFixedHeight(34)
    edit.setStyleSheet(input_style(pal))
    return edit


def combo(pal, items, index=0, width=260):
    box = ChevronCombo(pal)
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

    # ---- reconcile banner: the key inside the game is not in the vault yet
    banner = QWidget()
    banner.setObjectName("reconcileBanner")
    banner.setStyleSheet(
        "QWidget#reconcileBanner { background: %s; border: 1px solid %s; border-radius: 12px; }"
        % (pal["warn_soft"], pal["warn"])
    )
    banner_box = QHBoxLayout(banner)
    banner_box.setContentsMargins(14, 10, 12, 10)
    banner_box.setSpacing(10)
    banner_text = muted(pal, "", 9.5, "text")
    banner_text.setWordWrap(True)
    banner_box.addWidget(banner_text, 1)
    banner_save = PillButton(pal, "存进账号库", "primary", height=30, min_width=104)
    banner_skip = PillButton(pal, "不用管", "ghost", height=30, min_width=76)
    banner_box.addWidget(banner_save)
    banner_box.addWidget(banner_skip)
    banner.hide()
    col.addWidget(banner)

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

    def do_backup():
        if not ctrl:
            return
        default = time.strftime("备份 %m-%d %H:%M")
        name = _ask_text(page, pal, "备份命名", "给这次备份起个名字：", default)
        if name:
            ctrl.backup(name=name)

    btn_connect.clicked.connect(lambda: ctrl and ctrl.connect(current_serial()))
    btn_scan.clicked.connect(lambda: ctrl and ctrl.scan_ports())
    refresh.clicked.connect(lambda: ctrl and ctrl.refresh_devices())
    btn_open.clicked.connect(lambda: ctrl and ctrl.launch_game())
    btn_backup.clicked.connect(lambda _=False: do_backup())

    reconcile_state = {"payload": None}

    def on_reconcile(payload):
        reconcile_state["payload"] = payload
        if not payload:
            banner.hide()
            return
        source = payload.get("source") or "游戏里"
        serial = payload.get("serial") or ""
        banner_text.setText("「%s」（%s）里的 key 不在账号库里，要存一份吗？" % (source, serial))
        banner.show()

    def save_reconcile():
        payload = reconcile_state.get("payload")
        if not payload or not ctrl:
            return
        name = _ask_text(page, pal, "存进账号库", "给它起个名字：",
                         time.strftime("游戏内快照 %m-%d %H:%M"))
        if name:
            ctrl.save_reconcile(payload, name)

    def skip_reconcile():
        payload = reconcile_state.get("payload")
        if payload and ctrl:
            ctrl.dismiss_reconcile(payload.get("digest"))

    banner_save.clicked.connect(lambda _=False: save_reconcile())
    banner_skip.clicked.connect(lambda _=False: skip_reconcile())

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
        ctrl.reconcile_ready.connect(on_reconcile)
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


def _ask_text(parent, pal, title, label, default=""):
    return dialogs.ask_text(parent, pal, title, label, default=default)


def _qr_pixmap(text, size=248):
    from PySide6.QtGui import QPixmap
    from app import qrcodegen
    code = qrcodegen.QrCode.encode_text(text, qrcodegen.QrCode.Ecc.MEDIUM)
    n = code.get_size()
    scale = max(2, size // (n + 8))
    pix = QPixmap((n + 8) * scale, (n + 8) * scale)
    pix.fill(QColor("white"))
    painter = QPainter(pix)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#101828"))
    for y in range(n):
        for x in range(n):
            if code.get_module(x, y):
                painter.drawRect((x + 4) * scale, (y + 4) * scale, scale, scale)
    painter.end()
    return pix


def _show_qr(parent, pal, name, key_text):
    dialogs.show_qr(parent, pal, name, _qr_pixmap(key_text),
                    "手机版「任务 · 扫码导入」可以直接扫这张图")


def vault_page(shell):
    from .window import Page

    page = Page(shell.pal, "账号库", "本机保存的 AuthKey 备份")
    pal = shell.pal
    ctrl = getattr(shell, "controller", None)

    panel, col = card(shell)
    head = QWidget()
    head_row = QHBoxLayout(head)
    head_row.setContentsMargins(0, 0, 0, 0)
    head_row.setSpacing(8)
    head_row.addWidget(heading(pal, "全部账号"))
    count = muted(pal, "", 9.5, "text_faint")
    head_row.addWidget(count)
    game_label = muted(pal, "", 9.5, "text_faint")
    head_row.addWidget(game_label)
    head_row.addStretch(1)
    col.addWidget(head)

    actions = QWidget()
    actions_row = QHBoxLayout(actions)
    actions_row.setContentsMargins(0, 0, 0, 0)
    actions_row.setSpacing(8)
    actions_row.addStretch(1)
    clip_btn = PillButton(pal, "剪贴板", "ghost", height=32, min_width=72)
    folder_btn = PillButton(pal, "文件夹", "ghost", height=32, min_width=64)
    zip_btn = PillButton(pal, "打包导出", "ghost", height=32, min_width=84)
    lan_btn = PillButton(pal, "局域网", "ghost", height=32, min_width=68)
    import_btn = PillButton(pal, "导入 .hak", "ghost", height=32, min_width=92)
    for button in (clip_btn, folder_btn, zip_btn, lan_btn, import_btn):
        actions_row.addWidget(button)
    col.addWidget(actions)

    search = line(pal, "")
    search.setPlaceholderText("搜索名字或备注")
    search.setClearButtonEnabled(True)
    search.setMinimumWidth(160)
    search.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    col.addWidget(search)

    kinds = Segmented(pal, ["账号", "备份"], 0, width=180, height=32)
    col.addWidget(kinds)

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

    state = {"entries": [], "kind": "account"}

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
        title = QLabel("这里还没有记录")
        title.setFont(base.font(11, bold=True))
        title.setStyleSheet("background: transparent; color: %s;" % pal["text"])
        title.setAlignment(Qt.AlignCenter)
        hint = muted(pal, "去「任务」页做一次备份，或者导入 .hak / 从剪贴板导入", 9.5, "text_faint")
        hint.setAlignment(Qt.AlignCenter)
        inner.addWidget(title)
        inner.addWidget(hint)
        rows_box.addWidget(box)

    def export_row(entry):
        default = "%s_%s.hak" % (entry.get("name") or "housamo", time.strftime("%Y%m%d_%H%M"))
        path, _ = QFileDialog.getSaveFileName(panel, "导出 AuthKey", default,
                                              "AuthKey 文件 (*.hak)")
        if path and ctrl is not None:
            ctrl.export_entry(entry.get("id"), path)

    def delete_row(entry):
        ok = dialogs.confirm(panel, pal, "删除记录",
                             "确定删除「%s」吗？密钥会从本机账号库里移除。"
                             % (entry.get("name") or ""),
                             ok_text="删除", danger=True)
        if ok and ctrl is not None:
            ctrl.delete_entry(entry.get("id"))

    def rename_row(entry):
        text = _ask_text(panel, pal, "重命名", "新的名字：", entry.get("name") or "")
        if text and ctrl is not None:
            ctrl.rename_entry(entry.get("id"), text)

    def note_row(entry):
        text = _ask_text(panel, pal, "备注", "给这个账号写个备注（留空就清除）：", entry.get("note") or "")
        if ctrl is not None:
            ctrl.set_note(entry.get("id"), text)

    def qr_row(entry):
        if ctrl is None:
            return
        try:
            key = ctrl.service.vault.key_of(entry)
        except Exception:
            return
        _show_qr(panel, pal, entry.get("name"), key.decode("utf-8", "replace"))

    def restore_row(entry):
        if ctrl is not None:
            ctrl.restore_entry(entry.get("id"))

    def menu_row(entry, button):
        from PySide6.QtWidgets import QMenu
        menu = QMenu(button)
        menu.setFont(base.font(9.5))
        menu.addAction("还原到游戏", lambda: restore_row(entry))
        menu.addAction("导出 .hak", lambda: export_row(entry))
        menu.addAction("重命名", lambda: rename_row(entry))
        menu.addAction("备注", lambda: note_row(entry))
        menu.addAction("二维码", lambda: qr_row(entry))
        menu.addSeparator()
        menu.addAction("复制指纹", lambda: QApplication.clipboard().setText(entry.get("fingerprint") or ""))
        menu.addAction("删除", lambda: delete_row(entry))
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    def make_row(entry):
        row = QWidget()
        row.setObjectName("vaultRow")
        row.setStyleSheet(
            "QWidget#vaultRow { background: rgba(255,255,255,0.5); border-radius: 12px; }"
        )
        box = QHBoxLayout(row)
        box.setContentsMargins(14, 9, 10, 9)
        box.setSpacing(10)

        chip = QLabel(GAME_LABELS.get(entry.get("game"), "Housamo"))
        chip.setFont(base.font(8.5, bold=True))
        chip.setStyleSheet(
            "background: %s; color: %s; border-radius: 8px; padding: 2px 8px;" % (pal["accent_soft"], pal["accent"])
        )
        box.addWidget(chip)

        digest = entry.get("sha256") or ""
        if ctrl is not None and digest and digest == getattr(ctrl, "current_digest", ""):
            live = QLabel("游戏在用")
            live.setFont(base.font(8.5, bold=True))
            live.setStyleSheet(
                "background: %s; color: white; border-radius: 8px; padding: 2px 8px;" % pal["ok"]
            )
            box.addWidget(live)

        text_box = QVBoxLayout()
        text_box.setContentsMargins(0, 0, 0, 0)
        text_box.setSpacing(1)
        name = QLabel(entry.get("name") or "未命名账号")
        name.setFont(base.font(10.5, bold=True))
        name.setStyleSheet("background: transparent; color: %s;" % pal["text"])
        text_box.addWidget(name)
        under = entry.get("note") or entry.get("fingerprint") or ""
        if entry.get("note"):
            under = "%s  ·  %s" % (entry.get("note"), entry.get("fingerprint") or "")
        sub = QLabel(under)
        sub.setFont(base.mono(8.5) if not entry.get("note") else base.font(8.5))
        sub.setStyleSheet("background: transparent; color: %s;" % pal["text_faint"])
        text_box.addWidget(sub)
        box.addLayout(text_box)
        box.addStretch(1)

        when = muted(pal, (entry.get("created_at") or "")[:16], 9, "text_faint")
        box.addWidget(when)

        restore_btn = PillButton(pal, "还原", "ghost", height=28, min_width=60)
        restore_btn.clicked.connect(lambda _=False, e=entry: restore_row(e))
        box.addWidget(restore_btn)

        more = PillButton(pal, "⋯", "ghost", height=28, min_width=42)
        more.clicked.connect(lambda _=False, e=entry, b=more: menu_row(e, b))
        box.addWidget(more)
        return row

    def show_entries():
        clear_rows()
        entries = [e for e in state["entries"] if (e.get("kind") or "account") == state["kind"]]
        query = (search.text() or "").strip().lower()
        if query:
            entries = [e for e in entries
                       if query in (e.get("name") or "").lower()
                       or query in (e.get("note") or "").lower()]
        count.setText("%d 条" % len(entries) if entries else "")
        if not entries:
            empty_state()
            return
        for entry in entries:
            rows_box.addWidget(make_row(entry))

    def on_kind(index):
        state["kind"] = "account" if index == 0 else "backup"
        show_entries()

    kinds.changed.connect(on_kind)
    search.textChanged.connect(lambda _text: show_entries())

    def rebuild(entries):
        state["entries"] = list(entries or [])
        show_entries()

    def do_import():
        path, _ = QFileDialog.getOpenFileName(panel, "导入 AuthKey", "", "AuthKey 文件 (*.hak);;所有文件 (*)")
        if path and ctrl is not None:
            ctrl.import_file(path)

    def do_folder():
        path = QFileDialog.getExistingDirectory(panel, "选择要扫描的文件夹")
        if path and ctrl is not None:
            ctrl.import_folder(path)

    def do_zip():
        default = "%s_%s.zip" % (shell.settings.get("active_game") or "housamo", time.strftime("%Y%m%d"))
        path, _ = QFileDialog.getSaveFileName(panel, "打包导出", default, "Zip 压缩包 (*.zip)")
        if path and ctrl is not None:
            ctrl.bulk_export(path, "backup" if state["kind"] == "backup" else "account")

    def do_lan():
        if ctrl is None or ctrl.service is None:
            return
        from app import lanshare
        server = lanshare.LanServer(lambda: ctrl.service.lan_rows(),
                                    GAME_LABELS.get(ctrl.service.game.id, "Housamo"))
        try:
            url = server.start()
        except Exception as exc:
            ctrl.log("错误", "局域网服务起不来：%s" % exc)
            return
        try:
            dialogs.show_lan(
                panel, pal, url, server.code,
                "手机和电脑连同一个 Wi-Fi，然后在手机版输入这个地址")
        finally:
            server.stop()

    import_btn.clicked.connect(do_import)
    folder_btn.clicked.connect(do_folder)
    zip_btn.clicked.connect(do_zip)
    lan_btn.clicked.connect(do_lan)
    clip_btn.clicked.connect(lambda: ctrl and ctrl.import_clipboard())

    def show_game(game):
        game_label.setText("·  当前 %s" % GAME_LABELS.get(getattr(game, "id", ""), "Housamo"))

    if ctrl is not None:
        ctrl.vault_changed.connect(rebuild)
        ctrl.game_changed.connect(show_game)
        ctrl.current_changed.connect(lambda _digest: show_entries())
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
        ])
    return page


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

    panel, col = card(shell, head=page.head)

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
    addr_combo = ChevronCombo(pal)
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
        ports_field.setVisible(ports is None)
        if ports is None:
            note("已切到自定义配置：在「端口」里填，多个用逗号隔开")
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
    col.addWidget(Field(pal, "连接配置", profile_box, "选品牌自动填端口和地址", expand=True))
    ports_field = Field(pal, "端口", ports_edit, "多个用逗号隔开", expand=True)
    ports_field.setVisible(profile == "custom")
    col.addWidget(ports_field)

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

    addr_actions = QWidget()
    addr_actions_box = QHBoxLayout(addr_actions)
    addr_actions_box.setContentsMargins(0, 0, 0, 0)
    addr_actions_box.setSpacing(8)
    addr_actions_box.addWidget(get_btn)
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
    col.addWidget(Field(pal, "连接地址", addr_row, "可以只填端口，回车记住", top=True))

    # ---- ADB 路径：和 MAA 一样显示完整路径 + 选择
    adb_path = settings.get("adb_path") or ""
    adb_edit = line(pal, adb_path or "自动（内置 platform-tools）")
    adb_edit.setReadOnly(True)
    adb_edit.setCursorPosition(0)
    adb_edit.setToolTip(adb_path or "程序会优先用自带的 platform-tools")
    pick_adb = PillButton(pal, "选择", "ghost", height=30, min_width=68)
    reset_adb = PillButton(pal, "默认", "ghost", height=30, min_width=68)
    adb_edit_row = QWidget()
    adb_edit_box = QHBoxLayout(adb_edit_row)
    adb_edit_box.setContentsMargins(0, 0, 0, 0)
    adb_edit_box.addWidget(adb_edit, 1)
    adb_actions = QWidget()
    adb_actions_box = QHBoxLayout(adb_actions)
    adb_actions_box.setContentsMargins(0, 0, 0, 0)
    adb_actions_box.setSpacing(8)
    adb_actions_box.addWidget(pick_adb)
    adb_actions_box.addWidget(reset_adb)
    adb_actions_box.addStretch(1)
    adb_row = QWidget()
    adb_box = QVBoxLayout(adb_row)
    adb_box.setContentsMargins(0, 0, 0, 0)
    adb_box.setSpacing(8)
    adb_box.addWidget(adb_edit_row)
    adb_box.addWidget(adb_actions)

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
    col.addWidget(Field(pal, "ADB 路径", adb_row, "找不到设备时换一个", expand=True, top=True))

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
        note("端口已保存：%d 个" % len(ports))

    ports_edit.editingFinished.connect(commit_ports)

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


def _start_section(shell, page):
    pal = shell.pal
    settings = shell.settings
    ctrl = getattr(shell, "controller", None)

    panel, col = card(shell, head=page.head)

    def log(message, tag="提示"):
        if ctrl is not None:
            ctrl.log(tag, message)

    close_tray = Toggle(pal, bool(settings.get("close_to_tray")))
    close_tray.toggled.connect(lambda checked: settings.set("close_to_tray", bool(checked)))
    col.addWidget(Field(pal, "关闭时收进托盘", close_tray, "没开托盘图标时不起作用"))

    min_tray = Toggle(pal, bool(settings.get("minimize_to_tray")))
    min_tray.toggled.connect(lambda checked: settings.set("minimize_to_tray", bool(checked)))
    col.addWidget(Field(pal, "最小化时收进托盘", min_tray, "最小化后从托盘叫回"))

    from app import autostart

    boot = Toggle(pal, False)
    try:
        boot.blockSignals(True)
        boot.setChecked(bool(autostart.enabled()))
        boot.blockSignals(False)
    except Exception:
        boot.setEnabled(False)

    def on_boot(checked):
        try:
            autostart.set_enabled(bool(checked))
            log("开机自启已%s" % ("开启" if checked else "关闭"))
        except Exception as exc:
            log("开机自启设置失败：%s" % exc, "失败")
            boot.blockSignals(True)
            boot.setChecked(not checked)
            boot.blockSignals(False)

    boot.toggled.connect(on_boot)
    col.addWidget(Field(pal, "开机自启", boot, "登录 Windows 后自动启动"))

    low = Toggle(pal, bool(settings.get("low_mode")))

    def on_low(checked):
        if hasattr(shell, "apply_low_mode"):
            shell.apply_low_mode(bool(checked))
        log("低配模式已%s" % ("开启" if checked else "关闭"))

    low.toggled.connect(on_low)
    col.addWidget(Field(pal, "低配模式", low, "关壁纸模糊和卡片阴影"))

    hot = Toggle(pal, bool(shell.hotkey_active()))

    def on_hot(checked):
        ok = shell.set_hotkey(bool(checked)) if hasattr(shell, "set_hotkey") else False
        if checked and not ok:
            log("热键注册失败，可能被别的程序占用了", "失败")
            hot.blockSignals(True)
            hot.setChecked(False)
            hot.blockSignals(False)
            return
        log("全局热键已%s" % ("开启" if checked else "关闭"))

    hot.toggled.connect(on_hot)
    col.addWidget(Field(pal, "全局热键", hot, "Ctrl+Alt+A 随时呼出窗口"))
    page.add(panel)


def _notify_section(shell, page):
    pal = shell.pal
    settings = shell.settings
    ctrl = getattr(shell, "controller", None)
    from app import notify as notify_mod

    panel, col = card(shell, head=page.head)

    def log(message, tag="提示"):
        if ctrl is not None:
            ctrl.log(tag, message)

    balloon = Toggle(pal, bool(settings.get("notify_balloon")))
    balloon.toggled.connect(lambda checked: settings.set("notify_balloon", bool(checked)))
    col.addWidget(Field(pal, "托盘气泡", balloon, "备份完成时弹一条系统通知"))

    backup_tip = Toggle(pal, bool(settings.get("notify_on_backup")))
    backup_tip.toggled.connect(lambda checked: settings.set("notify_on_backup", bool(checked)))
    col.addWidget(Field(pal, "备份完成提醒", backup_tip, "没开气泡时只写运行日志"))

    update_tip = Toggle(pal, bool(settings.get("notify_on_update")))
    update_tip.toggled.connect(lambda checked: settings.set("notify_on_update", bool(checked)))
    col.addWidget(Field(pal, "新版本提醒", update_tip, "每发现一个新版本提醒一次"))

    web = Toggle(pal, bool(settings.get("notify_webhook")))

    def on_web(checked):
        settings.set("notify_webhook", bool(checked))
        log("网页通知已%s" % ("开启" if checked else "关闭"))

    web.toggled.connect(on_web)

    url = line(pal, settings.get("webhook_url") or "")
    url.setPlaceholderText("https://… 收到 JSON 的地址")
    url.setMinimumWidth(200)
    url.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    test_btn = PillButton(pal, "发测试", "ghost", height=32, min_width=76)
    url_row = QWidget()
    url_box = QHBoxLayout(url_row)
    url_box.setContentsMargins(0, 0, 0, 0)
    url_box.setSpacing(8)
    url_box.addWidget(url, 1)
    url_box.addWidget(test_btn)

    def save_url():
        settings.set("webhook_url", url.text().strip())

    def do_test():
        target = url.text().strip()
        if not target:
            log("先填 Webhook 地址", "失败")
            return
        settings.set("webhook_url", target)
        if ctrl is None or not hasattr(ctrl, "_bg"):
            return

        def work():
            return notify_mod.post_webhook(target, "东放 AuthKey 管家", "这是一条测试通知")

        def done(result):
            ok, detail = result if isinstance(result, tuple) else (False, str(result))
            if ok:
                log("测试通知已发出：%s" % (detail or "OK"))
            else:
                log("测试通知失败：%s" % detail, "失败")

        ctrl._bg(work, done)

    url.editingFinished.connect(save_url)
    test_btn.clicked.connect(lambda _=False: do_test())
    col.addWidget(Field(pal, "网页通知", web, "把提醒 POST 到自己的地址"))
    col.addWidget(Field(pal, "Webhook 地址", url_row, "支持 http(s)，失败只记日志", expand=True))
    page.add(panel)


def _look_section(shell, page):
    pal = shell.pal
    settings = shell.settings

    panel, col = card(shell, head=page.head)
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

    blur_timer = QTimer(blur_slider)
    blur_timer.setSingleShot(True)
    blur_timer.setInterval(60)

    def blur_preview():
        shell.set_backdrop(blur=blur_slider.value(), save=False)

    def on_blur(value):
        blur_readout.setText("%d" % value)
        blur_timer.start()

    def commit_blur():
        blur_timer.stop()
        shell.set_backdrop(blur=blur_slider.value())

    blur_slider.valueChanged.connect(on_blur)
    blur_slider.sliderReleased.connect(commit_blur)
    blur_timer.timeout.connect(blur_preview)
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

    panel, col = card(shell, head=page.head)
    check_toggle = Toggle(pal, bool(settings.get("auto_check_update")))

    def on_auto_check(checked):
        settings.set("auto_check_update", bool(checked))

    check_toggle.toggled.connect(on_auto_check)
    col.addWidget(Field(pal, "自动检查更新", check_toggle, "启动时检查一次"))

    source_values = ["auto", "github", "mirror"]
    source = Segmented(pal, ["自动", "GitHub", "镜像"], 0, width=260, height=34)
    try:
        source.set_index(source_values.index(settings.get("update_source") or "auto"))
    except ValueError:
        pass

    def on_source(index):
        settings.set("update_source", source_values[index])
        if ctrl is not None:
            ctrl.log("更新", "更新源：%s" % ["自动", "GitHub", "镜像"][index])

    source.changed.connect(on_source)
    col.addWidget(Field(pal, "更新源", source, "GitHub 慢时自动走镜像"))

    auto_download = Toggle(pal, bool(settings.get("auto_download_update")))

    def on_auto_download(checked):
        settings.set("auto_download_update", bool(checked))

    auto_download.toggled.connect(on_auto_download)
    col.addWidget(Field(pal, "自动下载新版本", auto_download,
                        "先在后台下好，装时再确认"))

    check_btn = PillButton(pal, "立即检查", "ghost", height=36, min_width=104)
    version = muted(pal, "当前版本 %s" % theme.APP_VERSION, 9.5, "text_faint")
    result = muted(pal, "还没检查过", 9.5, "text_faint")
    update_row = QWidget()
    update_box = QHBoxLayout(update_row)
    update_box.setContentsMargins(0, 0, 0, 0)
    update_box.setSpacing(12)
    update_box.addWidget(check_btn)
    update_box.addWidget(version)
    update_box.addStretch(1)
    check_btn.clicked.connect(lambda _=False: ctrl.check_update() if ctrl is not None else None)
    col.addWidget(update_row)
    col.addWidget(result)

    download = PillButton(pal, "打开下载页", "soft", height=34, min_width=112)

    def do_download():
        try:
            os.startfile(theme.REPO_URL + "/releases")
        except Exception:
            pass

    update_now = PillButton(pal, "立即更新", "primary", height=34, min_width=112)

    def do_update_now():
        if ctrl is not None:
            ctrl.install_update()

    update_now.clicked.connect(lambda _=False: do_update_now())
    download.clicked.connect(lambda _=False: do_download())
    download_row = QWidget()
    download_box = QHBoxLayout(download_row)
    download_box.setContentsMargins(0, 0, 0, 0)
    download_box.setSpacing(10)
    download_box.addWidget(update_now)
    download_box.addWidget(download)
    download_box.addStretch(1)
    col.addWidget(download_row)

    def on_checked(tag, newer):
        if newer:
            result.setText("发现新版本 %s" % (tag or "?"))
            result.setStyleSheet("background: transparent; color: %s;" % pal["accent"])
        else:
            result.setText("已是最新版本（%s）" % (tag or theme.APP_VERSION))
            result.setStyleSheet("background: transparent; color: %s;" % pal["text_muted"])

    if ctrl is not None:
        ctrl.update_checked.connect(on_checked)
    page.add(panel)


def _data_section(shell, page):
    pal = shell.pal
    ctrl = getattr(shell, "controller", None)
    settings = shell.settings

    panel, col = card(shell, head=page.head)
    from app import config as config_mod
    folder = line(pal, config_mod.app_dir())
    folder.setReadOnly(True)
    folder.setMinimumWidth(160)
    folder.setToolTip(config_mod.app_dir())
    folder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    folder.setCursorPosition(0)
    col.addWidget(Field(pal, "保存目录", folder, "账号库、壁纸和设置都放在这里", expand=True))

    vault_path = ""
    if ctrl is not None and getattr(ctrl, "service", None) is not None:
        vault_path = getattr(ctrl.service.vault, "path", "")
    game_name = GAME_LABELS.get(settings.get("active_game") or "housamo", "Housamo")
    vault_text = muted(pal, "%s · %s" % (game_name, vault_path or "还没建库"), 9, "text_faint")
    vault_text.setToolTip(vault_path or "")
    col.addWidget(Field(pal, "当前游戏库", vault_text, "切游戏后这里会跟着换"))

    from app import bulk as bulk_mod
    save_dir = line(pal, settings.get("save_dir") or "")
    save_dir.setPlaceholderText("选一个保存文件夹")
    save_dir.setMinimumWidth(130)
    save_dir.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    pick_dir = PillButton(pal, "选择", "ghost", height=32, min_width=60)
    clear_dir = PillButton(pal, "清除", "ghost", height=32, min_width=60)
    save_row = QWidget()
    save_box = QHBoxLayout(save_row)
    save_box.setContentsMargins(0, 0, 0, 0)
    save_box.setSpacing(8)
    save_box.addWidget(save_dir, 1)
    save_box.addWidget(pick_dir)
    save_box.addWidget(clear_dir)

    def apply_save_dir(path):
        settings.set("save_dir", path or "")
        save_dir.setText(path or "")
        if ctrl is not None:
            ctrl.log("提示", "自动导出目录：%s" % (path or "关闭"))

    def do_pick_dir():
        path = QFileDialog.getExistingDirectory(panel, "选择自动导出目录", save_dir.text() or "")
        if path:
            apply_save_dir(path)

    def do_clear_dir():
        apply_save_dir("")

    def do_manual_dir():
        apply_save_dir(save_dir.text().strip())

    pick_dir.clicked.connect(lambda _=False: do_pick_dir())
    clear_dir.clicked.connect(lambda _=False: do_clear_dir())
    save_dir.editingFinished.connect(do_manual_dir)
    col.addWidget(Field(pal, "自动导出", save_row,
                        "每次备份后写一份明文 AuthKey.txt，方便别的工具读取", expand=True))

    auto_backup = Toggle(pal, bool(settings.get("auto_backup")))
    hours = combo(pal, ["1 小时", "2 小时", "3 小时", "6 小时", "12 小时", "24 小时"], 3, 120)
    hours.setEnabled(bool(settings.get("auto_backup")))
    auto_row = QWidget()
    auto_box = QHBoxLayout(auto_row)
    auto_box.setContentsMargins(0, 0, 0, 0)
    auto_box.setSpacing(10)
    auto_box.addWidget(auto_backup)
    auto_box.addWidget(hours)

    hour_values = [1, 2, 3, 6, 12, 24]
    try:
        hours.setCurrentIndex(hour_values.index(int(settings.get("auto_backup_hours") or 6)))
    except ValueError:
        hours.setCurrentIndex(3)

    def on_auto_backup(checked):
        settings.set("auto_backup", bool(checked))
        hours.setEnabled(bool(checked))

    def on_hours(index):
        settings.set("auto_backup_hours", hour_values[index])

    auto_backup.toggled.connect(on_auto_backup)
    hours.currentIndexChanged.connect(on_hours)
    col.addWidget(Field(pal, "自动备份", auto_row, "程序开着时到点自动备份一次，没设备就跳过"))

    try:
        last_ts = float(settings.get("last_backup_at") or 0)
    except (TypeError, ValueError):
        last_ts = 0.0
    last_text = muted(pal, (time.strftime("%Y-%m-%d %H:%M", time.localtime(last_ts))
                            if last_ts else "还没备份过"), 9.5, "text_faint")
    backup_now = PillButton(pal, "立即备份", "ghost", height=32, min_width=88)
    last_row = QWidget()
    last_box = QHBoxLayout(last_row)
    last_box.setContentsMargins(0, 0, 0, 0)
    last_box.setSpacing(10)
    last_box.addWidget(last_text)
    last_box.addStretch(1)
    last_box.addWidget(backup_now)

    def do_backup_now():
        if ctrl is not None:
            ctrl.backup()

    backup_now.clicked.connect(lambda _=False: do_backup_now())
    col.addWidget(Field(pal, "上次备份", last_row, "手动备份和自动备份都会更新", expand=True))

    history = muted(pal, "", 9, "text_faint")
    history.setWordWrap(True)
    undo_last = PillButton(pal, "撤销上次导入", "ghost", height=32, min_width=104)
    history_row = QWidget()
    history_box = QHBoxLayout(history_row)
    history_box.setContentsMargins(0, 0, 0, 0)
    history_box.setSpacing(10)
    history_box.addWidget(history, 1)
    history_box.addWidget(undo_last)

    def game_key():
        if ctrl is not None and getattr(ctrl, "service", None) is not None:
            return ctrl.service.game.id
        return settings.get("active_game") or "housamo"

    def refresh_imports(*_args):
        items = bulk_mod.import_history(settings, game_key(), 5)
        if items:
            rows = ["%s  %s" % (item.get("at", ""), item.get("name", "")) for item in items]
            history.setText("最近导入：\n" + "\n".join(rows))
        else:
            history.setText("还没有导入记录")
        undo_last.setEnabled(bool(items))

    def do_undo_import():
        last = bulk_mod.last_import(settings, game_key())
        if not last:
            log("还没有导入记录", "提示")
            return
        entry_id = last.get("entry_id") or ""
        entry = None
        if ctrl is not None and getattr(ctrl, "service", None) is not None and entry_id:
            try:
                entry = ctrl.service.vault.get(entry_id)
            except Exception:
                entry = None
        if entry is None:
            bulk_mod.forget_import(settings, game_key())
            refresh_imports()
            log("那条账号已经不在库里，清掉了导入记录")
            return
        if not dialogs.confirm(panel, pal, "撤销上次导入",
                               "把「%s」从本机账号库里移除？\n\n只删这一份记录，设备上的 key 不受影响。"
                               % (entry.get("name") or ""), ok_text="移除", danger=True):
            return
        bulk_mod.forget_import(settings, game_key())
        if ctrl is not None:
            ctrl.delete_entry(entry_id)
        log("已撤销上次导入：%s" % (entry.get("name") or ""))

    def log(message, tag="提示"):
        if ctrl is not None:
            ctrl.log(tag, message)

    undo_last.clicked.connect(lambda _=False: do_undo_import())
    if ctrl is not None:
        ctrl.vault_changed.connect(refresh_imports)
        ctrl.game_changed.connect(refresh_imports)
    refresh_imports()
    col.addWidget(Field(pal, "导入记录", history_row, "导入过的最近 5 条", expand=True))

    keep = Segmented(pal, ["全部保留", "最近 10 份", "最近 30 天"],
                     0, width=300, height=34)
    keep_values = ["all", "10", "30d"]
    try:
        keep.set_index(keep_values.index(settings.get("backup_keep") or "all"))
    except ValueError:
        pass

    def on_keep(index):
        settings.set("backup_keep", keep_values[index])
        if ctrl is not None and ctrl.service is not None:
            try:
                removed = bulk_mod.prune_backups(ctrl.service.vault, keep_values[index])
                if removed:
                    ctrl.vault_changed.emit(ctrl.service.vault.entries)
                    ctrl.log("账号", "按保留策略清掉 %d 份旧备份" % removed)
            except Exception as exc:
                ctrl.log("失败", str(exc))

    keep.changed.connect(on_keep)
    col.addWidget(Field(pal, "备份保留", keep, "只影响「备份」分段，账号不会被自动删"))

    open_dir = PillButton(pal, "打开目录", "ghost", height=34, min_width=96)
    open_log = PillButton(pal, "更新日志", "ghost", height=34, min_width=96)
    copy_dir = PillButton(pal, "复制路径", "ghost", height=34, min_width=96)
    app_log = PillButton(pal, "运行日志", "ghost", height=34, min_width=96)

    def do_open(path):
        try:
            os.startfile(path)
        except Exception as exc:
            if ctrl is not None:
                ctrl.log("失败", "打不开目录：%s" % exc)

    def do_copy():
        QApplication.clipboard().setText(config_mod.app_dir())
        if ctrl is not None:
            ctrl.log("提示", "保存目录已复制到剪贴板")

    from app import logfile

    open_dir.clicked.connect(lambda _=False: do_open(config_mod.app_dir()))
    open_log.clicked.connect(lambda _=False: do_open(os.path.join(config_mod.app_dir(), "update.log")))
    copy_dir.clicked.connect(lambda _=False: do_copy())
    app_log.clicked.connect(lambda _=False: do_open(logfile.log_path()))
    data_row = QWidget()
    data_box = QHBoxLayout(data_row)
    data_box.setContentsMargins(0, 0, 0, 0)
    data_box.setSpacing(10)
    data_box.addWidget(open_dir)
    data_box.addWidget(open_log)
    data_box.addWidget(app_log)
    data_box.addStretch(1)

    copy_row = QWidget()
    copy_box = QHBoxLayout(copy_row)
    copy_box.setContentsMargins(0, 0, 0, 0)
    copy_box.addWidget(copy_dir)
    copy_box.addStretch(1)
    col.addWidget(data_row)
    col.addWidget(copy_row)

    diag_btn = PillButton(pal, "生成诊断包", "ghost", height=32, min_width=104)
    diag_row = QWidget()
    diag_box = QHBoxLayout(diag_row)
    diag_box.setContentsMargins(0, 0, 0, 0)
    diag_box.setSpacing(10)
    diag_box.addWidget(diag_btn)
    diag_box.addStretch(1)

    def do_diag():
        from app import diag as diag_mod
        from app import logfile as logfile_mod

        dest = os.path.join(logfile_mod.log_dir(), "diagnostics.zip")
        online = 0
        if ctrl is not None and getattr(ctrl, "service", None) is not None:
            try:
                online = sum(1 for dev in (ctrl.service.devices or []) if dev.online)
            except Exception:
                online = 0
        extra = "在线设备：%d" % online
        if ctrl is None or not hasattr(ctrl, "_bg"):
            return

        def done(result):
            ok, detail = result if isinstance(result, tuple) else (False, str(result))
            if not ok:
                log("诊断包生成失败：%s" % detail, "失败")
                return
            QApplication.clipboard().setText(detail)
            log("诊断包已生成，路径已复制：%s" % detail)

        ctrl._bg(lambda: diag_mod.build_bundle(dest, extra=extra), done)

    diag_btn.clicked.connect(lambda _=False: do_diag())
    col.addWidget(Field(pal, "诊断", diag_row, "打包日志和设置，方便排查问题"))

    def do_clear_vault():
        first = dialogs.confirm(
            panel, pal, "清空账号库",
            "会把账号库里所有记录删掉（备份分段也会一起清空）。导出过的 .hak 文件不受影响。",
            ok_text="继续", danger=True)
        if not first:
            return
        second = dialogs.confirm(
            panel, pal, "再确认一次",
            "确定要清空吗？清空后只能靠导出过的文件恢复。",
            ok_text="清空", danger=True)
        if second and ctrl is not None:
            ctrl.clear_vault()

    clear_vault_btn = PillButton(pal, "清空账号库", "danger", height=34, min_width=108)
    clear_vault_btn.clicked.connect(lambda _=False: do_clear_vault())
    danger_row = QWidget()
    danger_box = QHBoxLayout(danger_row)
    danger_box.setContentsMargins(0, 0, 0, 0)
    danger_box.addWidget(clear_vault_btn)
    danger_box.addStretch(1)
    col.addWidget(Field(pal, "危险操作", danger_row, "只删本机账号库，不动游戏里的 AuthKey"))
    page.add(panel)


def _security_section(shell, page):
    pal = shell.pal
    settings = shell.settings
    ctrl = getattr(shell, "controller", None)
    from app import applock
    from . import guard

    panel, col = card(shell, head=page.head)

    def log(message, tag="提示"):
        if ctrl is not None:
            ctrl.log(tag, message)

    def revert(toggle, value):
        toggle.blockSignals(True)
        toggle.setChecked(value)
        toggle.blockSignals(False)

    lock = Toggle(pal, applock.is_enabled(settings))

    def on_lock(checked):
        if checked:
            if applock.is_enabled(settings):
                return
            pin = guard.ask_pin(panel, pal, "应用锁", "设置 4-6 位数字 PIN：")
            if pin is None:
                revert(lock, False)
                return
            if not applock.valid_pin(pin):
                log("PIN 只能是 4-6 位数字", "失败")
                revert(lock, False)
                return
            again = guard.ask_pin(panel, pal, "应用锁", "再输一次确认：")
            if again != pin:
                log("两次输入不一致，应用锁没开", "失败")
                revert(lock, False)
                return
            applock.set_pin(settings, pin)
            log("应用锁已开启，下次启动要输 PIN")
        else:
            if not applock.is_enabled(settings):
                return
            pin = guard.ask_pin(panel, pal, "关闭应用锁", "输入当前 PIN：")
            if pin is None or not applock.check_pin(settings, pin):
                log("PIN 不对，应用锁还开着", "失败")
                revert(lock, True)
                return
            applock.clear_pin(settings)
            log("应用锁已关闭")

    lock.toggled.connect(on_lock)
    col.addWidget(Field(pal, "应用锁", lock, "启动时要求输入 4-6 位数字 PIN"))

    change = PillButton(pal, "修改 PIN", "ghost", height=32, min_width=96)
    change.setEnabled(applock.is_enabled(settings))

    def do_change():
        if not applock.is_enabled(settings):
            return
        pin = guard.ask_pin(panel, pal, "修改 PIN", "输入当前 PIN：")
        if pin is None or not applock.check_pin(settings, pin):
            log("PIN 不对，没改成", "失败")
            return
        fresh = guard.ask_pin(panel, pal, "修改 PIN", "设置新的 4-6 位数字 PIN：")
        if fresh is None or not applock.valid_pin(fresh):
            log("新 PIN 不合法", "失败")
            return
        again = guard.ask_pin(panel, pal, "修改 PIN", "再输一次确认：")
        if again != fresh:
            log("两次输入不一致", "失败")
            return
        applock.set_pin(settings, fresh)
        log("PIN 已更新")

    change.clicked.connect(lambda _=False: do_change())
    change_row = QWidget()
    change_box = QHBoxLayout(change_row)
    change_box.setContentsMargins(0, 0, 0, 0)
    change_box.addWidget(change)
    change_box.addStretch(1)
    col.addWidget(change_row)

    capture = Toggle(pal, bool(settings.get("no_capture")))

    def on_capture(checked):
        settings.set("no_capture", bool(checked))
        ok = guard.set_capture_guard(shell.window(), bool(checked)) if shell.window() else False
        if checked and not ok:
            log("这个系统不支持防截屏（需要 Win10 2004 以上）", "失败")
        else:
            log("防截屏已%s" % ("开启" if checked else "关闭"))

    capture.toggled.connect(on_capture)
    col.addWidget(Field(pal, "防截屏", capture, "截图和录屏时窗口会被遮住"))
    page.add(panel)


def _about_section(shell, page):
    pal = shell.pal

    panel, col = card(shell, head=page.head)
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

    def __init__(self, pal, parent=None, shell=None):
        super().__init__(parent)
        self.pal = pal
        self.alpha = (base.card_alpha(shell.settings.get("glass"))
                      if shell is not None and shell.settings is not None else 0.92)
        if shell is not None:
            shell.register_card(self)
        self.setFixedWidth(236)
        self.setSizePolicy(self.sizePolicy().horizontalPolicy().Fixed,
                           self.sizePolicy().verticalPolicy().Maximum)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(18, 26, -8, -18)
        base.paint_glass(p, self, self.pal, rect, 22, self.alpha,
                         base_key="card", border_strength=0.44)


class _SettingsPage(QWidget):
    """Settings with a MAA-style sub-navigation on the left."""

    def __init__(self, shell, pal):
        from .window import Page

        super().__init__()
        self.setStyleSheet("background: transparent;")
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)

        nav = _NavPanel(pal, self, shell=shell)
        nav_col = QVBoxLayout(nav)
        nav_col.setContentsMargins(40, 42, 26, 42)
        nav_col.setSpacing(6)
        title = QLabel("设置")
        title.setFont(base.font(11, bold=True))
        title.setStyleSheet("background: transparent; color: %s;" % pal["text_muted"])
        nav_col.addWidget(title)
        nav_col.addSpacing(16)

        self.stack = QStackedWidget(self)
        self.buttons = []
        sections = (
            ("connect", "连接设置", "连接设置", "设备、端口和记住的设备", _connect_section),
            ("start", "启动设置", "启动设置", "托盘、自启和全局热键", _start_section),
            ("look", "外观设置", "外观设置", "壁纸、透明度和主题", _look_section),
            ("notify", "通知设置", "通知设置", "备份提醒与网页通知", _notify_section),
            ("update", "更新设置", "更新设置", "检查并下载新版本", _update_section),
            ("data", "数据与存储", "数据与存储", "账号库和日志放在哪里", _data_section),
            ("security", "安全设置", "安全设置", "应用锁与防截屏", _security_section),
            ("about", "关于我们", "关于我们", "版本与项目主页", _about_section),
        )
        for index, (key, label, page_title, subtitle, builder) in enumerate(sections):
            button = SubNavButton(pal, label, nav)
            button.clicked.connect(lambda _=False, i=index: self.select(i))
            nav_col.addWidget(button)
            self.buttons.append(button)
            page = Page(pal, page_title, subtitle, head_in_card=True)
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
