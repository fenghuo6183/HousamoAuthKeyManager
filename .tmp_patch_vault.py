
import io, re
p = r"D:\123\4\win\qtui\pages.py"
src = io.open(p, encoding="utf-8").read()
start = src.index("def vault_page(shell):")
end = src.index("CONNECT_PROFILES = (")
new = '''def _ask_text(parent, title, label, default=""):
    from PySide6.QtWidgets import QInputDialog
    text, ok = QInputDialog.getText(parent, title, label, text=default)
    return text.strip() if ok else ""


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
    from PySide6.QtWidgets import QDialog
    dialog = QDialog(parent)
    dialog.setWindowTitle("账号二维码")
    dialog.setStyleSheet("QDialog { background: %s; } QLabel { color: %s; background: transparent; }"
                         % (pal["window"], pal["text"]))
    box = QVBoxLayout(dialog)
    box.setContentsMargins(22, 20, 22, 20)
    box.setSpacing(10)
    title = QLabel(name or "账号")
    title.setFont(base.font(11, bold=True))
    box.addWidget(title)
    pic = QLabel()
    pic.setPixmap(_qr_pixmap(key_text))
    pic.setAlignment(Qt.AlignCenter)
    box.addWidget(pic)
    hint = muted(pal, "手机版「任务 · 扫码导入」可以直接扫这张图", 9, "text_faint")
    hint.setAlignment(Qt.AlignCenter)
    box.addWidget(hint)
    close = PillButton(pal, "关闭", "ghost", height=32, min_width=88)
    close.clicked.connect(dialog.accept)
    row = QWidget()
    row_box = QHBoxLayout(row)
    row_box.setContentsMargins(0, 0, 0, 0)
    row_box.addStretch(1)
    row_box.addWidget(close)
    box.addWidget(row)
    dialog.exec()


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
    clip_btn = PillButton(pal, "剪贴板", "ghost", height=32, min_width=76)
    zip_btn = PillButton(pal, "打包导出", "ghost", height=32, min_width=88)
    lan_btn = PillButton(pal, "局域网", "ghost", height=32, min_width=72)
    import_btn = PillButton(pal, "导入 .hak", "ghost", height=32, min_width=96)
    for button in (clip_btn, zip_btn, lan_btn, import_btn):
        head_row.addWidget(button)
    col.addWidget(head)

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
        from PySide6.QtWidgets import QMessageBox
        answer = QMessageBox.question(panel, "删除记录",
                                      "确定删除「%s」吗？密钥会从本机账号库里移除。" % (entry.get("name") or ""),
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer == QMessageBox.Yes and ctrl is not None:
            ctrl.delete_entry(entry.get("id"))

    def note_row(entry):
        text = _ask_text(panel, "备注", "给这个账号写个备注（留空就清除）：", entry.get("note") or "")
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

    def rebuild(entries):
        state["entries"] = list(entries or [])
        show_entries()

    def do_import():
        path, _ = QFileDialog.getOpenFileName(panel, "导入 AuthKey", "", "AuthKey 文件 (*.hak);;所有文件 (*)")
        if path and ctrl is not None:
            ctrl.import_file(path)

    def do_zip():
        default = "%s_%s.zip" % (shell.settings.get("active_game") or "housamo", time.strftime("%Y%m%d"))
        path, _ = QFileDialog.getSaveFileName(panel, "打包导出", default, "Zip 压缩包 (*.zip)")
        if path and ctrl is not None:
            ctrl.bulk_export(path, "backup" if state["kind"] == "backup" else "account")

    def do_lan():
        if ctrl is None or ctrl.service is None:
            return
        from PySide6.QtWidgets import QDialog
        from app import lanshare
        server = lanshare.LanServer(lambda: ctrl.service.lan_rows(),
                                    GAME_LABELS.get(ctrl.service.game.id, "Housamo"))
        try:
            url = server.start()
        except Exception as exc:
            ctrl.log("错误", "局域网服务起不来：%s" % exc)
            return
        dialog = QDialog(panel)
        dialog.setWindowTitle("局域网分享")
        dialog.setStyleSheet("QDialog { background: %s; } QLabel { color: %s; background: transparent; }"
                             % (pal["window"], pal["text"]))
        box = QVBoxLayout(dialog)
        box.setContentsMargins(22, 20, 22, 20)
        box.setSpacing(10)
        title = QLabel("手机和电脑连同一个 Wi-Fi，然后在手机版输入这个地址")
        title.setWordWrap(True)
        title.setFont(base.font(10))
        box.addWidget(title)
        url_label = QLabel(url)
        url_label.setFont(base.mono(11))
        url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        box.addWidget(url_label)
        box.addWidget(muted(pal, "配对码 %s  ·  关掉这个窗口就停止分享" % server.code, 9, "text_faint"))
        close = PillButton(pal, "停止分享", "ghost", height=32, min_width=96)
        close.clicked.connect(dialog.accept)
        row = QWidget()
        row_box = QHBoxLayout(row)
        row_box.setContentsMargins(0, 0, 0, 0)
        row_box.addStretch(1)
        row_box.addWidget(close)
        box.addWidget(row)
        dialog.finished.connect(lambda _=0: server.stop())
        dialog.exec()

    import_btn.clicked.connect(do_import)
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


'''
io.open(p, "w", encoding="utf-8", newline="\n").write(src[:start] + new + src[end:])
print("rewritten", len(new))
