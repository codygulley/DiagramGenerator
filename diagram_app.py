"""
DiagramApp module — contains the DiagramApp class exported for a small launcher in main.py.
This file was created by extracting the DiagramApp class from main.py to improve modularity.
"""
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk, font as tkfont
from typing import List, Optional
import prefs
import json
from pathlib import Path
import sys
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

class Document:
    """Represents a single diagram document (model + UI widgets + controllers).

    The Document is intentionally lightweight: it mirrors the attributes the
    existing CanvasController and InteractionManager expect (so we can reuse
    those classes unchanged) and owns its canvas and listbox widgets.
    """
    def __init__(self, app, title: str = 'Untitled'):
        self.app = app  # reference back to DiagramApp for dialogs, palette, root
        self.title = title

        # Model
        self.actors = []
        self.interactions = []
        self.next_actor_id = 1
        self.current_file = None

        # Transient UI state (these mirror attributes expected by controllers)
        self.temp_line = None
        self.interaction_start_actor = None
        self.creating_interaction = False
        self.selected_actor_id = None
        self.dragging_actor = None
        self.drag_offset_x = 0

        # App-level helpers (copied from DiagramApp for controllers to use)
        try:
            self.palette = getattr(app, 'palette', {})
        except Exception:
            self.palette = {}
        self.dialogs = getattr(app, 'dialogs', None)
        self.root = getattr(app, 'root', None)

        # Widget refs (populated by create_ui)
        self.frame = None
        self.canvas = None
        self.interaction_listbox = None
        self.style_menu = None
        self.style_var = tk.StringVar(value='solid')
        self.new_interaction_style = tk.StringVar(value='solid')

        # Controllers (set after widgets created)
        self.canvas_controller = None
        self.interaction_manager = None

    def create_ui(self, parent):
        """Create UI for this document inside `parent` (a ttk.Frame used as tab).
        The layout mirrors the old single-document UI so the controllers behave
        identically.
        """
        self.frame = ttk.Frame(parent)
        # Left: canvas card
        left = ttk.Frame(self.frame)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(12,8), pady=12)
        canvas_card = ttk.Frame(left, style='Card.TFrame')
        canvas_card.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.canvas = tk.Canvas(canvas_card, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg=self.palette.get('canvas_bg', 'white'), highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Right: controls and listbox
        right = ttk.Frame(self.frame, width=300, style='TFrame')
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(8,12), pady=12)

        controls_card = ttk.Frame(right, style='Card.TFrame')
        controls_card.pack(padx=8, pady=(4,8), fill=tk.X)
        style_frame = ttk.Frame(controls_card, style='Card.TFrame')
        style_frame.pack(padx=8, pady=(0,8), anchor=tk.NW, fill=tk.X)
        tk.Label(style_frame, text='New Interaction Style:', bg=self.palette.get('card_bg'), fg=self.palette.get('text_fg'), font=self.app.small_font).pack(side=tk.LEFT)
        self._new_interaction_style_menu = tk.OptionMenu(style_frame, self.new_interaction_style, 'solid', 'dashed')
        self._new_interaction_style_menu.config(borderwidth=0, highlightthickness=0)
        self._new_interaction_style_menu.pack(side=tk.LEFT, padx=4)

        ttk.Label(right, text='Interactions:', style='Header.TLabel').pack(padx=8, pady=(12,0), anchor=tk.NW)
        list_card = ttk.Frame(right, style='Card.TFrame')
        list_card.pack(padx=8, pady=8, fill=tk.BOTH, expand=False)
        self.interaction_listbox = tk.Listbox(list_card, width=40, height=12, bd=0, highlightthickness=0, activestyle='none', bg=self.palette.get('card_bg'), fg=self.palette.get('text_fg'), selectbackground=self.palette.get('accent'), selectforeground='white')
        self.interaction_listbox.pack(padx=6, pady=6)

        btn_frame = ttk.Frame(list_card, style='Card.TFrame')
        btn_frame.pack(padx=8, pady=(6,8), fill=tk.X)
        self.up_btn = ttk.Button(btn_frame, text='Up', command=lambda: self.interaction_manager.move_interaction_up(), style='Accent.TButton')
        self.up_btn.grid(row=0, column=0, padx=4)
        self.down_btn = ttk.Button(btn_frame, text='Down', command=lambda: self.interaction_manager.move_interaction_down(), style='Accent.TButton')
        self.down_btn.grid(row=0, column=1, padx=4)
        self.edit_btn = ttk.Button(btn_frame, text='Edit', command=lambda: self.interaction_manager.edit_interaction_label(), style='Accent.TButton')
        self.edit_btn.grid(row=0, column=2, padx=4)
        self.delete_btn = ttk.Button(btn_frame, text='Delete', command=lambda: self.interaction_manager.delete_interaction(), style='Accent.TButton')
        self.delete_btn.grid(row=0, column=3, padx=4)

        self.style_menu = tk.OptionMenu(btn_frame, self.style_var, 'solid', 'dashed', command=lambda _=None: self.interaction_manager.on_style_change())
        self.style_menu.grid(row=0, column=4, padx=8)
        try:
            self.style_menu.configure(state='disabled')
        except Exception:
            pass
        try:
            self.up_btn.configure(state='disabled')
            self.down_btn.configure(state='disabled')
            self.edit_btn.configure(state='disabled')
            self.delete_btn.configure(state='disabled')
        except Exception:
            pass

        # Create controllers bound to this document
        self.canvas_controller = CanvasController(self)
        self.interaction_manager = InteractionManager(self)

        # Bind canvas events to the controller
        self.canvas.bind('<ButtonPress-1>', self.canvas_controller.on_canvas_press)
        self.canvas.bind('<B1-Motion>', self.canvas_controller.on_canvas_drag)
        self.canvas.bind('<ButtonRelease-1>', self.canvas_controller.on_canvas_release)
        try:
            self.canvas.bind('<Button-3>', lambda e: self.app.show_canvas_context_menu(e, doc=self))
            self.canvas.bind('<Button-2>', lambda e: self.app.show_canvas_context_menu(e, doc=self))
            self.canvas.bind('<Control-Button-1>', lambda e: self.app.show_canvas_context_menu(e, doc=self))
        except Exception:
            pass

        # Listbox selection handling
        self.interaction_listbox.bind('<<ListboxSelect>>', self.interaction_manager.on_interaction_select)

        return self.frame

    # Model actions
    def add_actor_dialog(self):
        name = self.app.dialogs.ask_string('Actor name', 'Enter actor name:')
        if not name:
            return
        x = 100 + (len(self.actors) * (ACTOR_WIDTH + 40))
        actor = Actor(id=self.next_actor_id, name=name, x=x)
        self.next_actor_id += 1
        self.actors.append(actor)
        try:
            self.canvas_controller.redraw()
        except Exception:
            pass

    def add_interaction(self, source: Actor, target: Actor, label: str = ''):
        if source.id == target.id:
            self.app.dialogs.info('Invalid', 'Cannot create interaction to the same actor')
            return
        style_val = self.new_interaction_style.get() if isinstance(self.new_interaction_style, tk.StringVar) else 'solid'
        self.interactions.append(Interaction(source_id=source.id, target_id=target.id, label=label, style=style_val))
        try:
            self.interaction_manager.update_interaction_listbox()
            self.canvas_controller.redraw()
        except Exception:
            pass

    def save_diagram(self, path: str):
        data = {'actors': [{'id': a.id, 'name': a.name, 'x': a.x, 'y': a.y} for a in self.actors],
                'interactions': [{'source_id': i.source_id, 'target_id': i.target_id, 'label': i.label, 'style': getattr(i, 'style', 'solid')} for i in self.interactions],
                'next_actor_id': self.next_actor_id}
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, indent=2)
        self.current_file = Path(path)
        return path

    def load_diagram(self, path: str):
        with open(path, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
        actors = []
        interactions = []
        for a in data.get('actors', []):
            actors.append(Actor(id=int(a['id']), name=str(a.get('name', '')), x=int(a.get('x', 100)), y=int(a.get('y', 20))))
        for it in data.get('interactions', []):
            interactions.append(Interaction(source_id=int(it['source_id']), target_id=int(it['target_id']), label=str(it.get('label', '')), style=str(it.get('style', 'solid'))))
        self.actors = actors
        self.interactions = interactions
        self.next_actor_id = int(data.get('next_actor_id', (max((a.id for a in actors), default=0) + 1)))
        try:
            self.interaction_manager.update_interaction_listbox()
            self.canvas_controller.redraw()
        except Exception:
            pass

    def apply_palette(self, palette: dict):
        """Update this document's widgets to use the provided palette."""
        try:
            self.palette = palette
        except Exception:
            pass
        try:
            if getattr(self, '_new_interaction_style_menu', None):
                try:
                    self._new_interaction_style_menu.configure(bg=palette.get('card_bg'), fg=palette.get('text_fg'), activebackground=palette.get('card_bg'), highlightthickness=0)
                    self._new_interaction_style_menu['menu'].configure(bg=palette.get('card_bg'), fg=palette.get('text_fg'), activebackground=palette.get('accent'))
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if getattr(self, 'style_menu', None):
                try:
                    self.style_menu.configure(bg=palette.get('card_bg'), fg=palette.get('text_fg'), activebackground=palette.get('card_bg'), highlightthickness=0)
                    self.style_menu['menu'].configure(bg=palette.get('card_bg'), fg=palette.get('text_fg'), activebackground=palette.get('accent'))
                except Exception:
                    pass
        except Exception:
            pass
        try:
            if getattr(self, 'canvas', None):
                self.canvas.configure(bg=palette.get('canvas_bg'))
        except Exception:
            pass

    # Helpers expected by controllers/manager (mirror prior DiagramApp API)
    def find_actor_at(self, x, y):
        if getattr(self, 'canvas_controller', None):
            return self.canvas_controller.find_actor_at(x, y)
        return None

    def get_actor_by_id(self, id_):
        if getattr(self, 'canvas_controller', None):
            return self.canvas_controller.get_actor_by_id(id_)
        # fallback: scan actors list
        for a in self.actors:
            if a.id == id_:
                return a
        return None

    def redraw(self):
        if getattr(self, 'canvas_controller', None):
            return self.canvas_controller.redraw()
        return None

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

        # Document management
        self.documents: List[Document] = []
        self.active_document: Optional[Document] = None

        # Layout
        # Notebook for document tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 8))

        # Track tab changes to update active document
        try:
            self.notebook.bind('<<NotebookTabChanged>>', lambda e: self._on_tab_changed(e))
        except Exception:
            pass

        # The Add Actor and Export buttons were removed in favor of the canvas context menu.
        # (Use right-click/context menu on the canvas to add actors or export.)

        # Application menu (menubar) with Theme submenu
        # Use a menubar radiobutton menu for theme selection instead of an in-pane OptionMenu.
        try:
            self.theme_var = tk.StringVar()
            disp = {'system':'System','light':'Light','dark':'Dark'}.get(self.user_theme_pref, 'System')
            self.theme_var.set(disp)

            self.menubar = tk.Menu(self.root)
            self.root.config(menu=self.menubar)

            # File menu: New / Open / Save / Save As / Export
            self._file_menu = tk.Menu(self.menubar, tearoff=0)
            self.menubar.add_cascade(label='File', menu=self._file_menu)
            # platform-aware accelerator labels
            accel_save = 'Cmd+S' if sys.platform == 'darwin' else 'Ctrl+S'
            accel_open = 'Cmd+O' if sys.platform == 'darwin' else 'Ctrl+O'
            accel_new = 'Cmd+N' if sys.platform == 'darwin' else 'Ctrl+N'
            accel_saveas = 'Cmd+Shift+S' if sys.platform == 'darwin' else 'Ctrl+Shift+S'

            self._file_menu.add_command(label=f'New\t{accel_new}', command=lambda: self.new_diagram(), accelerator=accel_new)
            self._file_menu.add_command(label=f'Open...\t{accel_open}', command=lambda: self.load_diagram_dialog(), accelerator=accel_open)
            self._file_menu.add_command(label=f'Save\t{accel_save}', command=lambda: self.save(), accelerator=accel_save)
            self._file_menu.add_command(label=f'Save As...\t{accel_saveas}', command=lambda: self.save_diagram_dialog(), accelerator=accel_saveas)
            self._file_menu.add_separator()
            self._file_menu.add_command(label='Export...', command=lambda: self.export_dialog())

            # Preferences / Theme menu
            self._prefs_menu = tk.Menu(self.menubar, tearoff=0)
            self.menubar.add_cascade(label='Preferences', menu=self._prefs_menu)
            # Theme submenu with radiobutton items bound to theme_var
            self._theme_menu = tk.Menu(self._prefs_menu, tearoff=0)
            self._prefs_menu.add_cascade(label='Theme', menu=self._theme_menu)
            # Radiobuttons update theme_var; invoke on change to apply
            self._theme_menu.add_radiobutton(label='System', variable=self.theme_var, value='System', command=self.on_theme_combo_change)
            self._theme_menu.add_radiobutton(label='Light', variable=self.theme_var, value='Light', command=self.on_theme_combo_change)
            self._theme_menu.add_radiobutton(label='Dark', variable=self.theme_var, value='Dark', command=self.on_theme_combo_change)
            # Global key bindings for accelerators (bind both Control and Command on macOS)
            try:
                # Use root.bind_all so accelerators work regardless of focus inside the app
                self.root.bind_all('<Control-s>', lambda e: (self.save() or True) and 'break')
                self.root.bind_all('<Control-o>', lambda e: (self.load_diagram_dialog() or True) and 'break')
                self.root.bind_all('<Control-n>', lambda e: (self.new_diagram() or True) and 'break')
                self.root.bind_all('<Control-Shift-S>', lambda e: (self.save_diagram_dialog() or True) and 'break')
                if sys.platform == 'darwin':
                    # Command key on macOS
                    self.root.bind_all('<Command-s>', lambda e: (self.save() or True) and 'break')
                    self.root.bind_all('<Command-o>', lambda e: (self.load_diagram_dialog() or True) and 'break')
                    self.root.bind_all('<Command-n>', lambda e: (self.new_diagram() or True) and 'break')
                    self.root.bind_all('<Command-Shift-S>', lambda e: (self.save_diagram_dialog() or True) and 'break')
            except Exception:
                pass
        except Exception:
            # Fall back silently if menu creation fails on a platform
            try:
                self.theme_var = tk.StringVar()
                self.theme_var.set('System')
            except Exception:
                pass

        # Create an initial empty document (adds a tab). Per-document UI is
        # created by `Document.create_ui` and controllers are bound to each
        # document; this app-level UI block was removed when we added tabs.
        try:
            self.new_diagram()
        except Exception:
            pass

    # ----------------- Actor management -----------------
    def add_actor_dialog(self):
        """Add an actor to the active document (or prompt harmlessly if none)."""
        doc = self.get_active_document()
        if doc:
            return doc.add_actor_dialog()
        # fallback: show dialog but no document to add to
        try:
            self.dialogs.ask_string("Actor name", "No document open to add actor to.")
        except Exception:
            pass

    # ----------------- Persistence (save/load) -----------------
    def new_diagram(self):
        # Create a new tab/document and select it
        doc = Document(self, title='Untitled')
        frame = doc.create_ui(self.notebook)
        self.documents.append(doc)
        self.notebook.add(frame, text=doc.title)
        self.notebook.select(frame)
        self.active_document = doc

    def save(self):
        doc = getattr(self, 'active_document', None)
        if not doc:
            return False
        if doc.current_file:
            try:
                doc.save_diagram(str(doc.current_file))
                return True
            except Exception as e:
                try:
                    self.dialogs.error('Save error', str(e))
                except Exception:
                    pass
                return False
        return self.save_diagram_dialog()

    def save_diagram_dialog(self):
        doc = getattr(self, 'active_document', None)
        if not doc:
            return False
        f = filedialog.asksaveasfilename(parent=self.root, defaultextension='.json', filetypes=[('Diagram JSON', '*.json')])
        if not f:
            return False
        try:
            doc.save_diagram(f)
            doc.current_file = Path(f)
            # update tab title
            try:
                idx = self.notebook.index(doc.frame)
                self.notebook.tab(idx, text=Path(f).name)
            except Exception:
                pass
            return True
        except Exception as e:
            try:
                self.dialogs.error('Save error', str(e))
            except Exception:
                pass
            return False

    def save_diagram(self, path: str):
        # Deprecated: keep for compatibility, but prefer document save.
        doc = getattr(self, 'active_document', None)
        if doc:
            return doc.save_diagram(path)
        raise RuntimeError('No active document')

    def load_diagram_dialog(self):
        f = filedialog.askopenfilename(parent=self.root, defaultextension='.json', filetypes=[('Diagram JSON', '*.json')])
        if not f:
            return False
        try:
            # Create a new document and load into it
            doc = Document(self, title=Path(f).name)
            frame = doc.create_ui(self.notebook)
            self.documents.append(doc)
            self.notebook.add(frame, text=doc.title)
            self.notebook.select(frame)
            self.active_document = doc
            doc.load_diagram(f)
            doc.current_file = Path(f)
            return True
        except Exception as e:
            try:
                self.dialogs.error('Load error', str(e))
            except Exception:
                pass
            return False

    def load_diagram(self, path: str):
        # Deprecated: prefer load via load_diagram_dialog which creates a new document
        doc = getattr(self, 'active_document', None)
        if not doc:
            raise RuntimeError('No active document to load into')
        return doc.load_diagram(path)

    # ----------------- Interaction management -----------------
    def add_interaction(self, source: Actor, target: Actor, label: str = ""):
        doc = self.get_active_document()
        if doc:
            return doc.add_interaction(source, target, label=label)
        try:
            self.dialogs.info("Invalid", "No open document to add interaction to")
        except Exception:
            pass

    def update_interaction_listbox(self):
        doc = self.get_active_document()
        if doc and doc.interaction_manager:
            return doc.interaction_manager.update_interaction_listbox()
        return None

    def select_interaction(self, idx: int):
        doc = self.get_active_document()
        if doc and doc.interaction_manager:
            return doc.interaction_manager.select_interaction(idx)
        return None

    def edit_interaction_label_at(self, idx: int):
        doc = self.get_active_document()
        if doc and doc.interaction_manager:
            return doc.interaction_manager.edit_interaction_label_at(idx)
        return None

    def on_interaction_select(self, event=None):
        doc = self.get_active_document()
        if doc and doc.interaction_manager:
            return doc.interaction_manager.on_interaction_select(event)
        return None

    def on_style_change(self):
        doc = self.get_active_document()
        if doc and doc.interaction_manager:
            return doc.interaction_manager.on_style_change()
        return None

    def move_interaction_up(self):
        doc = self.get_active_document()
        if doc and doc.interaction_manager:
            return doc.interaction_manager.move_interaction_up()
        return None

    def move_interaction_down(self):
        doc = self.get_active_document()
        if doc and doc.interaction_manager:
            return doc.interaction_manager.move_interaction_down()
        return None

    def edit_interaction_label(self):
        doc = self.get_active_document()
        if doc and doc.interaction_manager:
            return doc.interaction_manager.edit_interaction_label()
        return None

    def delete_interaction(self):
        doc = self.get_active_document()
        if doc and doc.interaction_manager:
            return doc.interaction_manager.delete_interaction()
        return None

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
            # Accent button: normal/active should use accent background with white text; disabled should use card background and muted text
            try:
                self.style.configure('Accent.TButton', foreground='white', background=palette['accent'], font=self.small_font)
                self.style.map('Accent.TButton',
                               background=[('disabled', palette.get('card_bg')), ('active', palette.get('accent')), ('!disabled', palette.get('accent'))],
                               foreground=[('disabled', palette.get('muted_fg')), ('!disabled', 'white')])
            except Exception:
                # Some ttk themes may not accept direct color maps; ignore failures.
                pass

            try:
                self.style.configure('Card.TCombobox', fieldbackground=palette['card_bg'], background=palette['card_bg'], foreground=palette['text_fg'])
            except Exception:
                pass
        except Exception:
            pass

        # update existing widgets that use tk colors (OptionMenus etc.)
        try:
            # style the new-interaction OptionMenu
            try:
                self._new_interaction_style_menu.configure(bg=palette['card_bg'], fg=palette.get('text_fg'), activebackground=palette['card_bg'], highlightthickness=0)
                self._new_interaction_style_menu['menu'].configure(bg=palette['card_bg'], fg=palette.get('text_fg'), activebackground=palette['accent'])
            except Exception:
                pass
        except Exception:
            pass

        try:
            # style the per-interaction OptionMenu (dropdown used to pick line type for selected interaction)
            if hasattr(self, 'style_menu') and self.style_menu is not None:
                try:
                    self.style_menu.configure(bg=palette['card_bg'], fg=palette['text_fg'], activebackground=palette['card_bg'], highlightthickness=0)
                    self.style_menu['menu'].configure(bg=palette['card_bg'], fg=palette['text_fg'], activebackground=palette['accent'])
                except Exception:
                    pass
        except Exception:
            pass

        # propagate palette to all open documents (their widgets & canvases)
        try:
            for doc in getattr(self, 'documents', []):
                try:
                    doc.apply_palette(palette)
                except Exception:
                    pass
        except Exception:
            pass

        # re-draw to apply color changes
        try:
            # redraw active document
            doc = self.get_active_document()
            if doc and getattr(doc, 'canvas_controller', None):
                doc.canvas_controller.redraw()
        except Exception:
            pass

        return

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
            # If an Export button exists in the UI it would be disabled while exporting;
            # but the button was removed in favor of the context menu. Guard the reference.
            try:
                if hasattr(self, 'export_btn'):
                    self.export_btn.config(state='disabled')
            except Exception:
                pass
            try:
                try:
                    # Prefer active document's canvas
                    doc = self.get_active_document()
                    canvas = None
                    if doc and getattr(doc, 'canvas', None):
                        canvas = doc.canvas
                    # If no document canvas available, error out
                    if canvas is None:
                        raise RuntimeError('No open document to export')
                    export_canvas(canvas, self.root, out_path, transparent=bool(trans_var.get()))
                    self.dialogs.info("Export", f"Exported to {out_path}")
                except Exception as e:
                    try:
                        self.dialogs.error("Export error", str(e))
                    except Exception:
                        pass
            finally:
                try:
                    if hasattr(self, 'export_btn'):
                        self.export_btn.config(state='normal')
                except Exception:
                    pass

        ttk.Button(btns, text='Choose file & Export', command=choose_and_export, style='Accent.TButton').pack(side=tk.RIGHT, padx=6)
        ttk.Button(btns, text='Cancel', command=lambda: dlg.destroy(), style='Accent.TButton').pack(side=tk.RIGHT, padx=6)

        on_fmt_change()
        dlg.wait_window()

    def show_canvas_context_menu(self, event, doc: Optional[Document] = None):
        """Show a right-click context menu on the canvas with common actions.

        The menu provides 'Add Actor' and 'Export...' entries. We post the menu at
        the pointer location so it feels native.
        """
        # Create a menu and keep a transient reference so it's not GC'd while shown.
        menu = None
        try:
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label='Add Actor', command=lambda: (doc.add_actor_dialog() if doc else None))
            menu.add_separator()
            menu.add_command(label='Export...', command=lambda: self.export_dialog())
            self._context_menu = menu
            # Determine screen coords for the popup. Some event objects (from root.bind_all)
            # may not provide x_root/y_root reliably, so fall back to the current pointer.
            try:
                x_root = int(event.x_root)
                y_root = int(event.y_root)
            except Exception:
                x_root = int(self.root.winfo_pointerx())
                y_root = int(self.root.winfo_pointery())
            # Use tk_popup for cross-platform behavior and then release the grab.
            menu.tk_popup(x_root, y_root)
        except Exception:
            try:
                if menu:
                    menu.unpost()
            except Exception:
                pass
        finally:
            try:
                if menu is not None:
                    menu.grab_release()
            except Exception:
                pass
            try:
                self._context_menu = None
            except Exception:
                pass

    def _on_tab_changed(self, event):
        try:
            sel = event.widget.select()
            # find document with matching frame
            for doc in self.documents:
                if str(doc.frame) == sel:
                    self.active_document = doc
                    return
            # fallback: if index returned, map by index
            try:
                idx = event.widget.index(sel)
                self.active_document = self.documents[idx] if idx < len(self.documents) else None
            except Exception:
                self.active_document = None
        except Exception:
            self.active_document = None

    # Helper to get active document
    def get_active_document(self) -> Optional[Document]:
        return getattr(self, 'active_document', None)

    # Delegate methods for single-document operations (kept for compatibility)
    def find_actor_at(self, x, y) -> Optional[Actor]:
        doc = self.get_active_document()
        if doc and doc.canvas_controller:
            return doc.canvas_controller.find_actor_at(x, y)
        return None

    def get_actor_by_id(self, id_: int) -> Optional[Actor]:
        doc = self.get_active_document()
        if doc and doc.canvas_controller:
            return doc.canvas_controller.get_actor_by_id(id_)
        return None

    def redraw(self):
        doc = self.get_active_document()
        if doc and doc.canvas_controller:
            return doc.canvas_controller.redraw()
        return None
