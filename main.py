"""
Simple Sequence Diagram Editor (Tkinter)

- Add actors (boxes at the top). Drag actors horizontally.
- Create interactions by toggling "New Interaction" and dragging from one actor to another.
- Interactions are ordered; the right-hand list shows interactions and allows moving up/down, editing labels, and deleting.

Run: python main.py
"""
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk, font as tkfont
from typing import List, Optional
import tempfile
import os
import shutil
import json
import platform
import subprocess

from models import Actor, Interaction, ACTOR_WIDTH, ACTOR_HEIGHT, ACTOR_TOP_Y, INTERACTION_START_Y, INTERACTION_V_GAP, CANVAS_WIDTH, CANVAS_HEIGHT, LABEL_COLOR, INDEX_COLOR, ACTOR_TEXT_COLOR, PREVIEW_LINE_COLOR
from dialogs import ThemedDialogs
import export_utils
try:
    from PIL import Image, ImageGrab
except Exception:
    try:
        from PIL import Image
        ImageGrab = None
    except Exception:
        Image = None
        ImageGrab = None

ACTOR_WIDTH = 120
ACTOR_HEIGHT = 40
ACTOR_TOP_Y = 20
INTERACTION_START_Y = 120
INTERACTION_V_GAP = 60
CANVAS_WIDTH = 1000
CANVAS_HEIGHT = 700

# Canvas color constants (modern, readable)
LABEL_COLOR = "#222222"     # interaction label text (dark)
INDEX_COLOR = "#666666"     # small index/sequence number
ACTOR_TEXT_COLOR = "#111111"
PREVIEW_LINE_COLOR = "#999999"

class DiagramApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Sequence Diagram Editor")
        # Modernize UI: use ttk styles, fonts and soft background
        self.root.configure(background="#f5f7fa")
        self.style = ttk.Style()
        try:
            # prefer a clean theme
            self.style.theme_use('clam')
        except Exception:
            pass
        # fonts
        default_font = tkfont.nametofont("TkDefaultFont")
        self.header_font = default_font.copy()
        self.header_font.configure(size=11, weight='bold')
        self.small_font = default_font.copy()
        self.small_font.configure(size=9)

        # Theme & preferences: load saved pref and detect system
        self.config = self.load_preferences()
        self.user_theme_pref = self.config.get('theme', 'system')
        # determine effective theme
        eff = self.user_theme_pref
        if eff == 'system':
            eff = self.detect_system_theme()
        # palette will be set by apply_theme
        self.apply_theme(eff)

        # dialog helpers (use themed dialogs when possible, fallback to BasicDialogs)
        try:
            self.dialogs = ThemedDialogs(self)
        except Exception:
            try:
                from dialogs import BasicDialogs
                self.dialogs = BasicDialogs(self.root)
            except Exception:
                self.dialogs = None

        self.actors: List[Actor] = []
        self.interactions: List[Interaction] = []
        self.next_actor_id = 1

        self.dragging_actor: Optional[Actor] = None
        self.drag_offset_x = 0

        self.creating_interaction = False
        self.interaction_start_actor: Optional[Actor] = None
        self.temp_line = None

        # Layout
        # Left area (canvas) in a white 'card'
        self.left_frame = ttk.Frame(root, style='TFrame')
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12,8), pady=12)

        canvas_card = ttk.Frame(self.left_frame, style='Card.TFrame')
        canvas_card.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.canvas = tk.Canvas(canvas_card, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg=self.palette.get('canvas_bg', 'white'), highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.right_frame = ttk.Frame(root, width=300, style='TFrame')
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(8,12), pady=12)

        self.add_actor_btn = ttk.Button(self.right_frame, text="Add Actor", command=self.add_actor_dialog, style='Accent.TButton')
        self.add_actor_btn.pack(padx=8, pady=8, anchor=tk.N, fill=tk.X)

        # Theme selector (System / Light / Dark)
        theme_frame = ttk.Frame(self.right_frame, style='TFrame')
        theme_frame.pack(padx=8, pady=(0,6), fill=tk.X)
        ttk.Label(theme_frame, text='Theme:', style='TLabel').pack(side=tk.LEFT)
        # Use a tk.OptionMenu so we can style the dropdown reliably across themes
        self.theme_var = tk.StringVar()
        disp = {'system':'System','light':'Light','dark':'Dark'}.get(self.user_theme_pref, 'System')
        self.theme_var.set(disp)
        self.theme_menu = tk.OptionMenu(theme_frame, self.theme_var, 'System', 'Light', 'Dark', command=self.on_theme_combo_change)
        self.theme_menu.config(borderwidth=0, highlightthickness=0)
        self.theme_menu.pack(side=tk.LEFT, padx=6)
        try:
            # also watch for programmatic changes to the variable
            self.theme_var.trace_add('write', lambda *_: self.on_theme_combo_change())
        except Exception:
            try:
                self.theme_var.trace('w', lambda *_: self.on_theme_combo_change())
            except Exception:
                pass

        # Controls card: keep interaction controls on a white card so labels sit on white
        controls_card = ttk.Frame(self.right_frame, style='Card.TFrame')
        controls_card.pack(padx=8, pady=(4,8), fill=tk.X)

        self.new_interaction_var = tk.IntVar()
        # Use a tk.Checkbutton with explicit white background so it visually sits on the card
        self.new_interaction_cb = tk.Checkbutton(controls_card, text="New Interaction (drag)", variable=self.new_interaction_var, command=self.toggle_new_interaction, bd=0, highlightthickness=0, bg=self.palette.get('card_bg'), activebackground=self.palette.get('card_bg'), fg=self.palette.get('text_fg'), selectcolor=self.palette.get('accent'))
        try:
            self.new_interaction_cb.config(font=self.small_font)
        except Exception:
            pass
        self.new_interaction_cb.pack(padx=8, pady=8, anchor=tk.NW, fill=tk.X)

        # Style selector for new interactions (placed on controls_card so background is white)
        self.new_interaction_style = tk.StringVar(value="solid")
        style_frame = ttk.Frame(controls_card, style='Card.TFrame')
        style_frame.pack(padx=8, pady=(0,8), anchor=tk.NW, fill=tk.X)
        # Use tk.Radiobuttons with explicit white background to match the card
        tk.Label(style_frame, text="New Interaction Style:", bg=self.palette.get('card_bg'), fg=self.palette.get('text_fg'), font=self.small_font).pack(side=tk.LEFT)
        r1 = tk.Radiobutton(style_frame, text="Solid", variable=self.new_interaction_style, value="solid", bd=0, highlightthickness=0, bg=self.palette.get('card_bg'), activebackground=self.palette.get('card_bg'), fg=self.palette.get('text_fg'), selectcolor=self.palette.get('accent'), activeforeground=self.palette.get('text_fg'))
        r1.pack(side=tk.LEFT, padx=4)
        r2 = tk.Radiobutton(style_frame, text="Dashed", variable=self.new_interaction_style, value="dashed", bd=0, highlightthickness=0, bg=self.palette.get('card_bg'), activebackground=self.palette.get('card_bg'), fg=self.palette.get('text_fg'), selectcolor=self.palette.get('accent'), activeforeground=self.palette.get('text_fg'))
        r2.pack(side=tk.LEFT, padx=4)
        # keep references so we can update colours when theme changes
        self._theme_r1 = r1
        self._theme_r2 = r2

        ttk.Label(self.right_frame, text="Interactions:", style='Header.TLabel').pack(padx=8, pady=(12,0), anchor=tk.NW)
        # Keep a simple Listbox but place it inside a styled frame
        list_card = ttk.Frame(self.right_frame, style='Card.TFrame')
        list_card.pack(padx=8, pady=8, fill=tk.BOTH, expand=False)
        self.interaction_listbox = tk.Listbox(list_card, width=40, height=12, bd=0, highlightthickness=0, activestyle='none', bg=self.palette.get('card_bg'), fg=self.palette.get('text_fg'), selectbackground=self.palette.get('accent'), selectforeground='white')
        self.interaction_listbox.pack(padx=6, pady=6)

        # Place action buttons and style combobox inside the list_card so they sit on the white card
        btn_frame = ttk.Frame(list_card, style='Card.TFrame')
        btn_frame.pack(padx=8, pady=(6,8), fill=tk.X)
        ttk.Button(btn_frame, text="Up", command=self.move_interaction_up, style='Accent.TButton').grid(row=0, column=0, padx=4)
        ttk.Button(btn_frame, text="Down", command=self.move_interaction_down, style='Accent.TButton').grid(row=0, column=1, padx=4)
        ttk.Button(btn_frame, text="Edit", command=self.edit_interaction_label, style='Accent.TButton').grid(row=0, column=2, padx=4)
        ttk.Button(btn_frame, text="Delete", command=self.delete_interaction, style='Accent.TButton').grid(row=0, column=3, padx=4)
        # Style combobox for the selected interaction (styled to match card)
        self.style_var = tk.StringVar(value="solid")
        # Replace the ttk Combobox with a tk.OptionMenu to ensure consistent styling in dark theme
        self.style_menu = tk.OptionMenu(btn_frame, self.style_var, 'solid', 'dashed', command=lambda v: self.on_style_change())
        self.style_menu.grid(row=0, column=4, padx=8)
        # disable until an interaction is selected
        try:
            self.style_menu.configure(state='disabled')
        except Exception:
            pass

        # Export button (opens a modal with export options)
        self.export_btn = ttk.Button(self.right_frame, text="Export", command=self.export_dialog, style='Accent.TButton')
        self.export_btn.pack(padx=8, pady=8, fill=tk.X)

        # Bind canvas events
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)

        # bind selection change to update style dropdown
        self.interaction_listbox.bind('<<ListboxSelect>>', self.on_interaction_select)
        # trace style var changes to update the selected interaction
        try:
            # Python >=3.6 uses trace_add
            self.style_var.trace_add('write', lambda *_: self.on_style_change())
        except Exception:
            # fallback to trace for older versions
            self.style_var.trace('w', lambda *_: self.on_style_change())

        self.redraw()

    # ----------------- Actor management -----------------
    def add_actor_dialog(self):
        name = self.dialogs.ask_string("Actor name", "Enter actor name:")
        if not name:
            return
        x = 100 + (len(self.actors) * (ACTOR_WIDTH + 40))
        actor = Actor(id=self.next_actor_id, name=name, x=x)
        self.next_actor_id += 1
        self.actors.append(actor)
        self.redraw()

    def find_actor_at(self, x, y) -> Optional[Actor]:
        for actor in self.actors:
            left = actor.x - ACTOR_WIDTH // 2
            right = actor.x + ACTOR_WIDTH // 2
            top = actor.y
            bottom = actor.y + ACTOR_HEIGHT
            if left <= x <= right and top <= y <= bottom:
                return actor
        return None

    # ----------------- Interaction management -----------------
    def toggle_new_interaction(self):
        self.creating_interaction = bool(self.new_interaction_var.get())
        if not self.creating_interaction:
            self.interaction_start_actor = None
            if self.temp_line:
                self.canvas.delete(self.temp_line)
                self.temp_line = None

    def add_interaction(self, source: Actor, target: Actor, label: str = ""):
        if source.id == target.id:
            self.dialogs.info("Invalid", "Cannot create interaction to the same actor")
            return
        # use selected new-interaction style by default
        style = getattr(self, 'new_interaction_style', None)
        if style and isinstance(style, tk.StringVar):
            style_val = style.get()
        else:
            style_val = 'solid'

        self.interactions.append(Interaction(source_id=source.id, target_id=target.id, label=label, style=style_val))
        self.update_interaction_listbox()
        self.redraw()

    def update_interaction_listbox(self):
        # preserve current selection index
        try:
            cur_sel = self.interaction_listbox.curselection()
            cur_idx = cur_sel[0] if cur_sel else None
        except Exception:
            cur_idx = None

        self.interaction_listbox.delete(0, tk.END)
        for i, inter in enumerate(self.interactions):
            src = self.get_actor_by_id(inter.source_id)
            tgt = self.get_actor_by_id(inter.target_id)
            src_name = src.name if src else f"id:{inter.source_id}"
            tgt_name = tgt.name if tgt else f"id:{inter.target_id}"
            s = f"{i+1}. {src_name} -> {tgt_name} [{inter.style}]: {inter.label}"
            self.interaction_listbox.insert(tk.END, s)

        # restore selection if possible
        if cur_idx is not None and 0 <= cur_idx < len(self.interactions):
            try:
                self.interaction_listbox.select_set(cur_idx)
                # make sure dropdown reflects selection
                self.on_interaction_select()
            except Exception:
                pass

    def select_interaction(self, idx: int):
        """Select an interaction in the listbox by index and update UI."""
        try:
            self.interaction_listbox.select_clear(0, tk.END)
            self.interaction_listbox.select_set(idx)
            self.interaction_listbox.see(idx)
            self.on_interaction_select()
        except Exception:
            pass

    def edit_interaction_label_at(self, idx: int):
        """Edit label for interaction at index idx (invoked from canvas)."""
        if idx < 0 or idx >= len(self.interactions):
            return
        inter = self.interactions[idx]
        new_label = self.dialogs.ask_string("Edit label", "Enter new label:", initial=inter.label, parent=self.root)
        if new_label is None:
            return
        inter.label = new_label
        self.update_interaction_listbox()
        self.redraw()

    def on_interaction_select(self, event=None):
        sel = self.interaction_listbox.curselection()
        if not sel:
            # disable dropdown
            try:
                self.style_menu.configure(state='disabled')
            except Exception:
                pass
            return
        idx = sel[0]
        inter = self.interactions[idx]
        # set dropdown to current style and enable it
        try:
            self.style_var.set(inter.style)
            try:
                self.style_menu.configure(state='normal')
            except Exception:
                pass
        except Exception:
            pass

    def on_style_change(self):
        sel = self.interaction_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < 0 or idx >= len(self.interactions):
            return
        new_style = self.style_var.get()
        inter = self.interactions[idx]
        if inter.style != new_style:
            inter.style = new_style
            self.update_interaction_listbox()
            self.redraw()

    def move_interaction_up(self):
        sel = self.interaction_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx == 0:
            return
        self.interactions[idx-1], self.interactions[idx] = self.interactions[idx], self.interactions[idx-1]
        self.update_interaction_listbox()
        self.interaction_listbox.select_set(idx-1)
        self.redraw()

    def move_interaction_down(self):
        sel = self.interaction_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.interactions)-1:
            return
        self.interactions[idx+1], self.interactions[idx] = self.interactions[idx], self.interactions[idx+1]
        self.update_interaction_listbox()
        self.interaction_listbox.select_set(idx+1)
        self.redraw()

    def edit_interaction_label(self):
        sel = self.interaction_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        inter = self.interactions[idx]
        new_label = self.dialogs.ask_string("Edit label", "Enter new label:", initial=inter.label)
        if new_label is None:
            return
        inter.label = new_label
        self.update_interaction_listbox()
        self.redraw()

    def delete_interaction(self):
        sel = self.interaction_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        del self.interactions[idx]
        self.update_interaction_listbox()
        self.redraw()

    # ----------------- Theme & preferences -----------------
    def get_config_path(self) -> str:
        """Return a path to the user config file for saving preferences."""
        try:
            if os.name == 'nt':
                appdata = os.environ.get('APPDATA') or os.path.expanduser('~')
                cfg_dir = os.path.join(appdata, 'DiagramGenerator')
            else:
                cfg_dir = os.path.expanduser('~')
            os.makedirs(cfg_dir, exist_ok=True)
            return os.path.join(cfg_dir, 'diagram_config.json')
        except Exception:
            return os.path.join(os.path.expanduser('~'), '.diagram_config.json')

    def load_preferences(self) -> dict:
        path = self.get_config_path()
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def save_preferences(self):
        path = self.get_config_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f)
        except Exception:
            pass

    def detect_system_theme(self) -> str:
        """Return 'dark' or 'light' based on OS settings where possible."""
        try:
            system = platform.system()
            if system == 'Windows':
                try:
                    import winreg
                    key = r'SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize'
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
                        val = winreg.QueryValueEx(k, 'AppsUseLightTheme')[0]
                        return 'light' if val == 1 else 'dark'
                except Exception:
                    return 'light'
            elif system == 'Darwin':
                try:
                    p = subprocess.run(['defaults', 'read', '-g', 'AppleInterfaceStyle'], capture_output=True, text=True)
                    out = (p.stdout or p.stderr or '').strip()
                    return 'dark' if out.lower().startswith('dark') else 'light'
                except Exception:
                    return 'light'
        except Exception:
            pass
        return 'light'

    def apply_theme(self, theme_name: str):
        """Apply either 'light' or 'dark' palette to the app chrome and widgets."""
        theme = theme_name.lower() if theme_name else 'light'
        if theme == 'dark':
            # Neutral dark greys; make the app chrome & modals match the canvas for a consistent dark UI
            palette = {
                # set app background equal to canvas background so modals and root chrome all use the same dark gray
                'app_bg': '#111217',
                'card_bg': '#111217',
                'text_fg': '#e6eef6',
                'muted_fg': '#9aa3ad',
                'accent': '#4a90e2',
                'card_border': '#0b1116',
                # make canvas match card for consistent dark look
                'canvas_bg': '#111217',
                # actor box colors: slightly lighter than card so text pops
                'actor_fill': '#181b22',
                'actor_outline': '#262a31',
                'actor_text': '#e6eef6',
                'label_fg': '#e6eef6',
                'index_fg': '#9aa3ad',
                'preview_line': '#6b7280',
                'lifeline': '#2f3440'
            }
        else:
            palette = {
                'app_bg': '#f5f7fa',
                'card_bg': '#ffffff',
                'text_fg': '#111827',
                'muted_fg': '#6b7280',
                'accent': '#4a90e2',
                'card_border': '#e6e9ef',
                # keep canvas same as card for consistent look
                'canvas_bg': '#ffffff',
                'actor_text': '#111111',
                'label_fg': '#222222',
                'index_fg': '#666666',
                'preview_line': '#999999',
                'actor_fill': '#f0f0ff',
                'actor_outline': '#000000',
                'lifeline': '#888888'
             }
        self.palette = palette
        # apply root bg
        try:
            self.root.configure(background=palette['app_bg'])
        except Exception:
            pass
        # apply ttk styles
        try:
            self.style.configure('TFrame', background=palette['app_bg'])
            self.style.configure('Card.TFrame', background=palette['card_bg'])
            self.style.configure('Card.TLabel', background=palette['card_bg'], font=self.small_font, foreground=palette['text_fg'])
            self.style.configure('TLabel', background=palette['app_bg'], font=self.small_font, foreground=palette['text_fg'])
            self.style.configure('Header.TLabel', background=palette['app_bg'], font=self.header_font, foreground=palette['text_fg'])
            self.style.configure('Accent.TButton', foreground='white', background=palette['accent'], font=self.small_font)
            self.style.map('Accent.TButton', background=[('active', palette['accent'])])
            try:
                self.style.configure('Card.TCombobox', fieldbackground=palette['card_bg'], background=palette['card_bg'], foreground=palette['text_fg'])
            except Exception:
                pass
        except Exception:
            pass
        # update existing widgets that use tk colors
        try:
            # checkbutton background and selection color
            self.new_interaction_cb.configure(bg=palette['card_bg'], activebackground=palette['card_bg'], fg=palette['text_fg'], selectcolor=palette['accent'], activeforeground=palette['text_fg'])
        except Exception:
            pass
        try:
            # radiobuttons
            self._theme_r1.configure(bg=palette['card_bg'], activebackground=palette['card_bg'], fg=palette['text_fg'], selectcolor=palette['accent'], activeforeground=palette['text_fg'])
            self._theme_r2.configure(bg=palette['card_bg'], activebackground=palette['card_bg'], fg=palette['text_fg'], selectcolor=palette['accent'], activeforeground=palette['text_fg'])
        except Exception:
            pass
        # combobox
        try:
            # style OptionMenus (widget and menu)
            self.style_menu.configure(bg=palette['card_bg'], fg=palette['text_fg'], activebackground=palette['card_bg'], highlightthickness=0)
            self.style_menu['menu'].configure(bg=palette['card_bg'], fg=palette['text_fg'], activebackground=palette['accent'])
        except Exception:
            pass
        try:
            self.theme_menu.configure(bg=palette['card_bg'], fg=palette['text_fg'], activebackground=palette['card_bg'], highlightthickness=0)
            self.theme_menu['menu'].configure(bg=palette['card_bg'], fg=palette['text_fg'], activebackground=palette['accent'])
        except Exception:
            pass
        # canvas background
        try:
            self.canvas.configure(bg=palette['canvas_bg'])
        except Exception:
            pass
        # store current theme
        self.current_theme = theme
        # re-draw to apply color changes
        try:
            self.redraw()
        except Exception:
            pass

    def on_theme_combo_change(self, val=None):
        """Handle changes from the Theme OptionMenu. Accepts either the passed value or reads the StringVar."""
        try:
            if isinstance(val, str):
                sel = val.lower()
            else:
                sel = (self.theme_var.get() or 'system').lower()
        except Exception:
            sel = 'system'

        if sel.startswith('s'):
            key = 'system'
        elif sel.startswith('d'):
            key = 'dark'
        else:
            key = 'light'

        self.user_theme_pref = key
        try:
            self.config['theme'] = self.user_theme_pref
            self.save_preferences()
        except Exception:
            pass

        eff = self.user_theme_pref
        if eff == 'system':
            eff = self.detect_system_theme()
        self.apply_theme(eff)

    def export_dialog(self):
        """Open export modal; choose PNG/JPEG and optional transparency for PNG."""
        if Image is None:
            self.dialogs.error("Export error", "Pillow (PIL) is required for exporting images. Please install it: pip install pillow")
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Export options")
        dlg.transient(self.root)
        dlg.grab_set()
        try:
            dlg.configure(background=self.palette.get('app_bg', '#f5f7fa'))
        except Exception:
            pass

        card = ttk.Frame(dlg, style='Card.TFrame')
        card.pack(padx=12, pady=12, fill=tk.BOTH, expand=True)
        ttk.Label(card, text="Export options", style='Header.TLabel').pack(anchor=tk.W, padx=8, pady=(6,4))

        fmt_var = tk.StringVar(value='png')
        fmt_row = ttk.Frame(card, style='Card.TFrame')
        fmt_row.pack(fill=tk.X, padx=8, pady=(4,2))
        tk.Label(fmt_row, text="Format:", bg=self.palette.get('card_bg', '#ffffff'), font=self.small_font).grid(row=0, column=0, sticky=tk.W)
        rpng = tk.Radiobutton(fmt_row, text='PNG', variable=fmt_var, value='png', bd=0, highlightthickness=0, bg=self.palette.get('card_bg'), activebackground=self.palette.get('card_bg'), fg=self.palette.get('text_fg'), selectcolor=self.palette.get('accent'), activeforeground=self.palette.get('text_fg'))
        rpng.grid(row=0, column=1, padx=8)
        rjpg = tk.Radiobutton(fmt_row, text='JPEG', variable=fmt_var, value='jpg', bd=0, highlightthickness=0, bg=self.palette.get('card_bg'), activebackground=self.palette.get('card_bg'), fg=self.palette.get('text_fg'), selectcolor=self.palette.get('accent'), activeforeground=self.palette.get('text_fg'))
        rjpg.grid(row=0, column=2, padx=8)

        trans_var = tk.IntVar(value=1)
        trans_cb = tk.Checkbutton(card, text='Transparent background (PNG)', variable=trans_var, bd=0, highlightthickness=0, bg=self.palette.get('card_bg'), activebackground=self.palette.get('card_bg'), fg=self.palette.get('text_fg'), selectcolor=self.palette.get('accent'), activeforeground=self.palette.get('text_fg'))
        try:
            trans_cb.config(font=self.small_font)
        except Exception:
            pass
        trans_cb.pack(anchor=tk.W, padx=8, pady=(6,4))

        def on_fmt_change(*_):
            try:
                if fmt_var.get() == 'png':
                    trans_cb.configure(state=tk.NORMAL)
                else:
                    trans_cb.configure(state=tk.DISABLED)
            except Exception:
                pass

        try:
            fmt_var.trace_add('write', lambda *_: on_fmt_change())
        except Exception:
            fmt_var.trace('w', lambda *_: on_fmt_change())

        btns = ttk.Frame(card, style='Card.TFrame')
        btns.pack(fill=tk.X, padx=8, pady=(8,4))

        def choose_and_export():
            ftypes = [("PNG", "*.png"), ("JPEG", "*.jpg;*.jpeg")]
            default_ext = '.png' if fmt_var.get() == 'png' else '.jpg'
            out_path = filedialog.asksaveasfilename(parent=dlg, defaultextension=default_ext, filetypes=ftypes)
            if not out_path:
                return
            try:
                dlg.destroy()
            except Exception:
                pass
            try:
                self.export_btn.config(state='disabled')
            except Exception:
                pass
            try:
                self._do_export(out_path, transparent=bool(trans_var.get()))
            finally:
                try:
                    self.export_btn.config(state='normal')
                except Exception:
                    pass

        ttk.Button(btns, text='Choose file & Export', command=choose_and_export, style='Accent.TButton').pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text='Cancel', command=lambda: dlg.destroy(), style='Accent.TButton').pack(side=tk.RIGHT, padx=6)

        on_fmt_change()
        dlg.wait_window()

    def _do_export(self, out_path: str, transparent: bool = False):
        """Export the canvas to out_path. Supports transparency for PNG via chroma-key on canvas bg.

        Attempts PostScript -> Pillow route first (requires Ghostscript), falls back to ImageGrab on Windows.
        """
        if Image is None:
            self.dialogs.error("Export error", "Pillow (PIL) is required for exporting images. Please install it: pip install pillow")
            return

        gs_candidates = ["gswin64c", "gswin32c", "gs"]
        gs_path = None
        for name in gs_candidates:
            p = shutil.which(name)
            if p:
                gs_path = p
                break

        if not gs_path and ImageGrab is None:
            self.dialogs.error(
                "Export unavailable",
                "PostScript export requires Ghostscript and Pillow. Ghostscript was not found and ImageGrab fallback is not available.\n\nInstall Ghostscript (https://www.ghostscript.com/) and add it to your PATH, or install Pillow with ImageGrab support."
            )
            return

        if not gs_path and ImageGrab is not None:
            self.dialogs.info("Export fallback", "Ghostscript not found: export will use a screen-capture fallback (ImageGrab). Ensure the app window is visible on screen during export.")

        ps_path = None
        last_exc = None

        try:
            # PostScript -> Pillow route
            try:
                self.canvas.update()
                with tempfile.NamedTemporaryFile(delete=False, suffix='.ps') as tmp:
                    ps_path = tmp.name
                self.canvas.postscript(file=ps_path, colormode='color')
                img = Image.open(ps_path)
                if out_path.lower().endswith(('.jpg', '.jpeg')):
                    img = img.convert('RGB')
                else:
                    img = img.convert('RGBA')

                if out_path.lower().endswith('.png') and transparent:
                    try:
                        bg = self.canvas.cget('bg')
                        r16, g16, b16 = self.root.winfo_rgb(bg)
                        bg_rgb = (r16 // 256, g16 // 256, b16 // 256)
                    except Exception:
                        bg_rgb = (255, 255, 255)
                    tol = 10
                    img = img.convert('RGBA')
                    datas = img.getdata()
                    newData = []
                    for item in datas:
                        r, g, b, a = item
                        if (abs(r - bg_rgb[0]) <= tol and abs(g - bg_rgb[1]) <= tol and abs(b - bg_rgb[2]) <= tol):
                            newData.append((r, g, b, 0))
                        else:
                            newData.append((r, g, b, a))
                    img.putdata(newData)

                img.save(out_path)
                self.dialogs.info("Export", f"Exported to {out_path}")
                return
            except Exception as e:
                last_exc = e

            # ImageGrab fallback
            if ImageGrab is not None:
                try:
                    self.canvas.update()
                    x = self.canvas.winfo_rootx()
                    y = self.canvas.winfo_rooty()
                    w = self.canvas.winfo_width()
                    h = self.canvas.winfo_height()
                    bbox = (x, y, x + w, y + h)
                    img = ImageGrab.grab(bbox)
                    if out_path.lower().endswith(('.jpg', '.jpeg')):
                        img = img.convert('RGB')
                    else:
                        img = img.convert('RGBA')

                    if out_path.lower().endswith('.png') and transparent:
                        try:
                            bg = self.canvas.cget('bg')
                            r16, g16, b16 = self.root.winfo_rgb(bg)
                            bg_rgb = (r16 // 256, g16 // 256, b16 // 256)
                        except Exception:
                            bg_rgb = (255, 255, 255)
                        tol = 10
                        datas = img.getdata()
                        newData = []
                        for item in datas:
                            r, g, b, a = item
                            if (abs(r - bg_rgb[0]) <= tol and abs(g - bg_rgb[1]) <= tol and abs(b - bg_rgb[2]) <= tol):
                                newData.append((r, g, b, 0))
                            else:
                                newData.append((r, g, b, a))
                        img.putdata(newData)

                    img.save(out_path)
                    self.dialogs.info("Export", f"Exported to {out_path} (via ImageGrab fallback)")
                    return
                except Exception as e2:
                    last_exc = (last_exc, e2)
                    raise
                else:
                    raise RuntimeError("PostScript export failed and ImageGrab fallback is not available")
        except Exception as final_exc:
            msg = "Export failed."
            if isinstance(last_exc, tuple):
                msg += f"\nPostScript error: {last_exc[0]}\nImageGrab error: {last_exc[1]}"
            else:
                msg += f"\nError: {last_exc or final_exc}"
            msg += "\n\nIf the PostScript error mentions Ghostscript, install Ghostscript and add it to your PATH. On Windows you can also try the ImageGrab fallback (requires Pillow with ImageGrab)."
            self.dialogs.error("Export error", msg)
            return
        finally:
            try:
                if ps_path and os.path.exists(ps_path):
                    os.remove(ps_path)
            except Exception:
                pass

    # ----------------- Canvas events -----------------
    def on_canvas_press(self, event):
        x, y = event.x, event.y
        actor = self.find_actor_at(x, y)
        if actor and not self.creating_interaction:
            # start dragging actor
            self.dragging_actor = actor
            self.drag_offset_x = actor.x - x
        elif actor and self.creating_interaction:
            # start interaction from this actor
            self.interaction_start_actor = actor
        else:
            # click on blank area - deselect
            self.dragging_actor = None

    def on_canvas_drag(self, event):
        x, y = event.x, event.y
        if self.dragging_actor:
            # move actor horizontally
            new_x = x + self.drag_offset_x
            # clamp into canvas
            new_x = max(ACTOR_WIDTH//2 + 10, min(CANVAS_WIDTH - ACTOR_WIDTH//2 - 10, new_x))
            self.dragging_actor.x = new_x
            self.redraw()
        elif self.creating_interaction and self.interaction_start_actor:
            # draw temporary line from start actor center to current mouse
            sx = self.interaction_start_actor.x
            sy = INTERACTION_START_Y
            if self.temp_line:
                self.canvas.delete(self.temp_line)
            # preview style should match selected new-interaction style
            dash = None
            try:
                style = self.new_interaction_style.get()
            except Exception:
                style = 'solid'
            if style == 'dashed':
                dash = (6, 4)
            self.temp_line = self.canvas.create_line(sx, sy, x, y, arrow=tk.LAST, dash=dash, fill=self.palette.get('preview_line', PREVIEW_LINE_COLOR))

    def on_canvas_release(self, event):
        x, y = event.x, event.y
        if self.dragging_actor:
            self.dragging_actor = None
            return
        if self.creating_interaction and self.interaction_start_actor:
            target = self.find_actor_at(x, y)
            if not target:
                self.dialogs.info("Invalid", "Release on an actor to create an interaction")
            else:
                # create interaction then prompt for a label
                self.add_interaction(self.interaction_start_actor, target, label="")
                # prompt user for a label immediately
                try:
                    idx = len(self.interactions) - 1
                    new_label = self.dialogs.ask_string("Interaction label", "Enter label for this interaction:", parent=self.root)
                    if new_label is not None:
                        self.interactions[idx].label = new_label
                        self.update_interaction_listbox()
                        self.redraw()
                except Exception:
                    pass
            self.interaction_start_actor = None
            if self.temp_line:
                self.canvas.delete(self.temp_line)
                self.temp_line = None

    # ----------------- Helpers & drawing -----------------
    def get_actor_by_id(self, id_: int) -> Optional[Actor]:
        for a in self.actors:
            if a.id == id_:
                return a
        return None

    def redraw(self):
        self.canvas.delete("all")
        # draw actors
        for actor in self.actors:
            left = actor.x - ACTOR_WIDTH // 2
            top = actor.y
            right = actor.x + ACTOR_WIDTH // 2
            bottom = actor.y + ACTOR_HEIGHT
            actor.rect_id = self.canvas.create_rectangle(left, top, right, bottom, fill=self.palette.get('actor_fill', '#f0f0ff'), outline=self.palette.get('actor_outline', '#000'))
            actor.text_id = self.canvas.create_text(actor.x, actor.y + ACTOR_HEIGHT//2, text=actor.name, fill=self.palette.get('actor_text', ACTOR_TEXT_COLOR))
            # lifeline (dashed)
            lx = actor.x
            ly1 = bottom
            ly2 = CANVAS_HEIGHT - 20
            self.canvas.create_line(lx, ly1, lx, ly2, dash=(4,4), fill=self.palette.get('lifeline', '#888'))

        # draw interactions in order
        for i, inter in enumerate(self.interactions):
            src = self.get_actor_by_id(inter.source_id)
            tgt = self.get_actor_by_id(inter.target_id)
            if not src or not tgt:
                continue
            y = INTERACTION_START_Y + i * INTERACTION_V_GAP
            sx = src.x
            tx = tgt.x
            # draw line with arrow from source to target
            dash = None
            if getattr(inter, 'style', 'solid') == 'dashed':
                dash = (6, 4)
            line_color = self.palette.get('label_fg', LABEL_COLOR)
            if sx <= tx:
                # left to right
                line = self.canvas.create_line(sx, y, tx, y, arrow=tk.LAST, width=2, dash=dash, fill=line_color, tags=(f"interaction_{i}",))
            else:
                line = self.canvas.create_line(sx, y, tx, y, arrow=tk.LAST, width=2, dash=dash, fill=line_color, tags=(f"interaction_{i}",))
            # label and index
            midx = (sx + tx) // 2
            # label text sits above the line and is tagged so it can be clicked/edited too
            self.canvas.create_text(midx, y - 10, text=inter.label, fill=self.palette.get('label_fg', LABEL_COLOR), tags=(f"interaction_label_{i}", f"interaction_{i}"))
            self.canvas.create_text(40, y, text=str(i+1), fill=self.palette.get('index_fg', INDEX_COLOR))
            # bind canvas events for selection and editing (single-click selects, double-click edits label)
            try:
                self.canvas.tag_bind(f"interaction_{i}", "<Button-1>", lambda e, ii=i: self.select_interaction(ii))
                self.canvas.tag_bind(f"interaction_{i}", "<Double-Button-1>", lambda e, ii=i: self.edit_interaction_label_at(ii))
            except Exception:
                pass

        # if creating an interaction but no temp_line, draw a small hint line from mouse? no

        # update listbox (ensure selection remains valid)
        self.update_interaction_listbox()


if __name__ == "__main__":
    root = tk.Tk()
    app = DiagramApp(root)
    root.mainloop()

