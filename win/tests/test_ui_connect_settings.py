# -*- coding: utf-8 -*-
"""Connection controls belong in Settings, not on the task page.

The task page is for picking a device; scanning ports and typing a custom
address are setup work, so they live behind 设置 → 连接 (MuMu-style).
"""

import os
import tempfile
import unittest

os.environ["HOUSAMO_DATA_DIR"] = os.path.join(tempfile.mkdtemp(prefix="hak-conn-"), "data")
os.environ["HOUSAMO_NO_ADB"] = "1"

import tkinter as tk

from app import theme
from app.ui import App
from app.widgets import PillButton


def ancestors(widget):
    node = widget
    while node is not None:
        yield node
        try:
            node = node.master
        except Exception:
            node = None


def inside(widget, ancestor):
    return any(node is ancestor for node in ancestors(widget))


def walk(widget):
    yield widget
    try:
        children = widget.winfo_children()
    except Exception:
        return
    for child in children:
        for item in walk(child):
            yield item


class ConnectSettingsTest(unittest.TestCase):
    def setUp(self):
        theme.set_ui_scale(1.0)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = App(self.root)
        self.root.update()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_address_box_lives_in_settings(self):
        settings_cards = [card for card, _h in self.app.pages["settings"]]
        self.assertTrue(
            any(inside(self.app.addr_entry, card) for card in settings_cards),
            "自定义连接地址应该放在设置页的连接卡里")

    def test_task_page_no_longer_has_the_address_box(self):
        for card, _h in self.app.pages["tasks"]:
            self.assertFalse(inside(self.app.addr_entry, card),
                             "任务页不该再塞连接地址输入框")

    def test_task_page_offers_a_shortcut_to_connection_settings(self):
        found = None
        for card, _h in self.app.pages["tasks"]:
            for widget in walk(card):
                if isinstance(widget, PillButton) and widget.text == "连接设置":
                    found = widget
                    break
            if found is not None:
                break
        self.assertIsNotNone(found, "任务页需要一个跳到连接设置的入口")
        self.app._show_page("tasks")
        found.command()
        self.root.update()
        self.assertEqual(self.app.page, "settings")


if __name__ == "__main__":
    unittest.main()
