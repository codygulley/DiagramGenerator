"""Launcher for the Sequence Diagram Editor.

This file intentionally keeps a tiny bootstrap so IDE run configurations can stay pointing
at `main.py`. The application logic lives in `diagram_app.py`.
"""
from diagram_app import DiagramApp
import tkinter as tk


def main():
    root = tk.Tk()
    app = DiagramApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

