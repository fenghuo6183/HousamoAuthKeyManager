# -*- coding: utf-8 -*-
"""Entry point for the Windows client."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.ui import App  # noqa: E402
import tkinter as tk  # noqa: E402


def main():
    if "--selftest" in sys.argv:
        root = tk.Tk()
        root.withdraw()
        App(root)
        root.update()
        root.destroy()
        print("SELFTEST OK")
        return
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
