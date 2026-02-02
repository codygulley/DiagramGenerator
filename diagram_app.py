"""
DiagramApp module — contains the DiagramApp class exported for a small launcher in main.py.
This file was created by extracting the DiagramApp class from main.py to improve modularity.
"""
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk, font as tkfont
from typing import List, Optional
import prefs
from theme import palette_for_theme
from ui_utils import center_window

from models import (
    Actor,
    Interaction,
    ACTOR_WIDTH,
    ACTOR_HEIGHT,
    INTERACTION_START_Y,
    INTERACTION_V_GAP,
    CANVAS_WIDTH,
    CANVAS_HEIGHT,
    LABEL_COLOR,
    INDEX_COLOR,
    ACTOR_TEXT_COLOR,
    PREVIEW_LINE_COLOR,
)
from dialogs import ThemedDialogs
from export_utils import export_canvas
from canvas_controller import CanvasController
from interaction_manager import InteractionManager


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
        self.config = prefs.load_preferences()
        self.user_theme_pref = self.config.get('theme', 'system')
        eff = self.user_theme_pref
        if eff == 'system':
            eff = prefs.detect_system_theme()
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

        # Create controllers/managers and bind canvas events to them
        self.canvas_controller = CanvasController(self)
        self.interaction_manager = InteractionManager(self)
        self.canvas.bind("<ButtonPress-1>", self.canvas_controller.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.canvas_controller.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.canvas_controller.on_canvas_release)

        # bind selection change to update style dropdown
        self.interaction_listbox.bind('<<ListboxSelect>>', self.interaction_manager.on_interaction_select)

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
        self.interaction_manager.update_interaction_listbox()
        self.canvas_controller.redraw()

    def update_interaction_listbox(self):
        return self.interaction_manager.update_interaction_listbox()

    def select_interaction(self, idx: int):
        """Select an interaction in the listbox by index and update UI."""
        return self.interaction_manager.select_interaction(idx)

    def edit_interaction_label_at(self, idx: int):
        """Edit label for interaction at index idx (invoked from canvas)."""
        return self.interaction_manager.edit_interaction_label_at(idx)

    def on_interaction_select(self, event=None):
        return self.interaction_manager.on_interaction_select(event)

    def on_style_change(self):
        return self.interaction_manager.on_style_change()

    def move_interaction_up(self):
        return self.interaction_manager.move_interaction_up()

    def move_interaction_down(self):
        return self.interaction_manager.move_interaction_down()

    def edit_interaction_label(self):
        return self.interaction_manager.edit_interaction_label()

    def delete_interaction(self):
        return self.interaction_manager.delete_interaction()

    # ----------------- Theme & preferences -----------------
    def save_preferences(self):
        prefs.save_preferences(self.config)

    def apply_theme(self, theme_name: str):
        """Apply either 'light' or 'dark' palette to the app chrome and widgets."""
        palette = palette_for_theme(theme_name)
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
        self.current_theme = theme_name.lower() if theme_name else 'light'
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
            eff = prefs.detect_system_theme()
        self.apply_theme(eff)

    def export_dialog(self):
        """Open export modal; choose PNG/JPEG and optional transparency for PNG."""

        dlg = tk.Toplevel(self.root)
        dlg.title("Export options")
        dlg.transient(self.root)
        dlg.grab_set()
        try:
            center_window(dlg, self.root)
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
                try:
                    export_canvas(self.canvas, self.root, out_path, transparent=bool(trans_var.get()))
                    self.dialogs.info("Export", f"Exported to {out_path}")
                except Exception as e:
                    self.dialogs.error("Export error", str(e))
            finally:
                try:
                    self.export_btn.config(state='normal')
                except Exception:
                    pass

        ttk.Button(btns, text='Choose file & Export', command=choose_and_export, style='Accent.TButton').pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text='Cancel', command=lambda: dlg.destroy(), style='Accent.TButton').pack(side=tk.RIGHT, padx=6)

        on_fmt_change()
        dlg.wait_window()

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
                        self.interaction_manager.update_interaction_listbox()
                        self.canvas_controller.redraw()
                except Exception:
                    pass
            self.interaction_start_actor = None
            if self.temp_line:
                self.canvas.delete(self.temp_line)
                self.temp_line = None

    # ----------------- Helpers & drawing -----------------
    def find_actor_at(self, x, y) -> Optional[Actor]:
        return self.canvas_controller.find_actor_at(x, y)

    def get_actor_by_id(self, id_: int) -> Optional[Actor]:
        return self.canvas_controller.get_actor_by_id(id_)

    def redraw(self):
        return self.canvas_controller.redraw()
