import tkinter as tk
from tkinter import ttk
from typing import Optional

class ThemedDialogs:
    """Helper for themed modal dialogs.

    Usage:
        d = ThemedDialogs(app)
        name = d.ask_string("Title", "Prompt", initial="", parent=app.root)
        d.info("Title", "Message")
        d.error("Title", "Message")
    """
    def __init__(self, app):
        self.app = app

    def ask_string(self, title: str, prompt: str, initial: str = "", parent=None) -> Optional[str]:
        parent = parent or self.app.root
        dlg = tk.Toplevel(parent)
        dlg.title(title)
        dlg.transient(parent)
        dlg.grab_set()
        try:
            dlg.configure(background=self.app.palette.get('app_bg'))
        except Exception:
            pass

        card = ttk.Frame(dlg, style='Card.TFrame')
        card.pack(padx=12, pady=12, fill=tk.BOTH, expand=True)

        lbl = ttk.Label(card, text=prompt, style='Card.TLabel')
        lbl.pack(anchor=tk.W, padx=8, pady=(4,6))

        entry_bg = self.app.palette.get('actor_fill', self.app.palette.get('card_bg'))
        entry_fg = self.app.palette.get('text_fg')
        entry = tk.Entry(card, bg=entry_bg, fg=entry_fg, relief='solid')
        try:
            entry.insert(0, initial or "")
        except Exception:
            pass
        entry.pack(fill=tk.X, padx=8, pady=(0,8))

        result = {'value': None}

        def on_ok():
            try:
                result['value'] = entry.get()
            except Exception:
                result['value'] = None
            try:
                dlg.destroy()
            except Exception:
                pass

        def on_cancel():
            try:
                dlg.destroy()
            except Exception:
                pass

        btns = ttk.Frame(card, style='Card.TFrame')
        btns.pack(fill=tk.X, padx=8, pady=(6,4))
        ttk.Button(btns, text='OK', command=on_ok, style='Accent.TButton').pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text='Cancel', command=on_cancel, style='Accent.TButton').pack(side=tk.RIGHT, padx=6)

        entry.bind('<Return>', lambda e: on_ok())
        entry.bind('<Escape>', lambda e: on_cancel())
        entry.focus_set()

        dlg.wait_window()
        return result['value']

    def info(self, title: str, message: str, parent=None):
        parent = parent or self.app.root
        dlg = tk.Toplevel(parent)
        dlg.title(title)
        dlg.transient(parent)
        dlg.grab_set()
        try:
            dlg.configure(background=self.app.palette.get('app_bg'))
        except Exception:
            pass
        card = ttk.Frame(dlg, style='Card.TFrame')
        card.pack(padx=12, pady=12, fill=tk.BOTH, expand=True)
        ttk.Label(card, text=message, style='Card.TLabel', wraplength=400).pack(anchor=tk.W, padx=8, pady=(6,8))
        btns = ttk.Frame(card, style='Card.TFrame')
        btns.pack(fill=tk.X, padx=8, pady=(6,4))
        ttk.Button(btns, text='OK', command=dlg.destroy, style='Accent.TButton').pack(side=tk.RIGHT, padx=6)
        dlg.wait_window()

    def error(self, title: str, message: str, parent=None):
        # For now error uses same visual as info
        self.info(title, message, parent=parent)


class BasicDialogs:
    """Fallback dialogs using tkinter.simpledialog and messagebox when themed modals fail.

    API matches ThemedDialogs: ask_string, info, error.
    """
    def __init__(self, root):
        self.root = root

    def ask_string(self, title: str, prompt: str, initial: str = "", parent=None):
        from tkinter import simpledialog
        parent = parent or self.root
        try:
            return simpledialog.askstring(title, prompt, initialvalue=initial, parent=parent)
        except Exception:
            return None

    def info(self, title: str, message: str, parent=None):
        from tkinter import messagebox
        parent = parent or self.root
        try:
            messagebox.showinfo(title, message, parent=parent)
        except Exception:
            pass

    def error(self, title: str, message: str, parent=None):
        from tkinter import messagebox
        parent = parent or self.root
        try:
            messagebox.showerror(title, message, parent=parent)
        except Exception:
            pass
