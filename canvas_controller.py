"""CanvasController: handles canvas drawing and mouse interactions.

This module is intentionally independent from `diagram_app` to avoid circular imports; it
receives the `app` instance (DiagramApp) and reads/writes state on it.
"""
import tkinter as tk
from typing import Optional
from math import hypot
from models import ACTOR_WIDTH, ACTOR_HEIGHT, INTERACTION_START_Y, INTERACTION_V_GAP, CANVAS_HEIGHT
from models import Actor


class CanvasController:
    def __init__(self, app):
        self.app = app
        self.canvas = app.canvas
        # transient state for press/drag handling
        self.pressed_actor: Optional[Actor] = None
        self.press_x = None
        self.press_y = None
        # whether we're currently dragging to create an interaction (from press)
        self.dragging_interaction = False
        # small movement threshold to distinguish click vs drag
        self._drag_threshold = 6

    def find_actor_at(self, x, y) -> Optional[Actor]:
        for actor in self.app.actors:
            left = actor.x - ACTOR_WIDTH // 2
            right = actor.x + ACTOR_WIDTH // 2
            top = actor.y
            bottom = actor.y + ACTOR_HEIGHT
            if left <= x <= right and top <= y <= bottom:
                return actor
        return None

    def get_actor_by_id(self, id_: int) -> Optional[Actor]:
        for a in self.app.actors:
            if a.id == id_:
                return a
        return None

    # Canvas event handlers
    def on_canvas_press(self, event):
        x, y = event.x, event.y
        actor = self.find_actor_at(x, y)
        # If the click landed on an interaction canvas item, don't clear selection here;
        # let the item's tag bindings handle selection. Check current items under pointer.
        try:
            items = self.canvas.find_overlapping(x, y, x, y)
            for it in items:
                tags = self.canvas.gettags(it) or ()
                for t in tags:
                    if isinstance(t, str) and t.startswith('interaction_'):
                        # parse index from tag 'interaction_{i}' and select that interaction
                        try:
                            idx = int(t.split('_', 1)[1])
                            try:
                                self.app.interaction_manager.select_interaction(idx)
                            except Exception:
                                pass
                        except Exception:
                            pass
                        # done handling the click
                        return
        except Exception:
            pass
        # Clear any interaction listbox selection when clicking canvas (clicking an actor will select it on release)
        try:
            self.app.interaction_listbox.select_clear(0, tk.END)
            try:
                self.app.style_menu.configure(state='disabled')
            except Exception:
                pass
        except Exception:
            pass

        # Detect if Shift is held (modifier bit 0x0001) — use Shift to move actors
        shift_held = False
        try:
            shift_held = bool(event.state & 0x0001)
        except Exception:
            shift_held = False

        if actor:
            if shift_held:
                # Start actor dragging immediately when Shift is held
                try:
                    self.app.dragging_actor = actor
                    self.app.drag_offset_x = actor.x - x
                except Exception:
                    self.app.dragging_actor = None
                # clear transient press/interaction state
                self.pressed_actor = None
                self.press_x = None
                self.press_y = None
                self.dragging_interaction = False
            else:
                # don't immediately start dragging the actor; record as a potential press for click vs interaction
                self.pressed_actor = actor
                self.press_x = x
                self.press_y = y
                # ensure actor-drag isn't active
                try:
                    self.app.dragging_actor = None
                except Exception:
                    pass
        else:
            # click on blank area - deselect actor and interaction
            self.pressed_actor = None
            self.press_x = None
            self.press_y = None
            try:
                self.app.selected_actor_id = None
            except Exception:
                pass
            try:
                # redraw to clear any selection highlight
                self.redraw()
            except Exception:
                pass

    def on_canvas_drag(self, event):
        x, y = event.x, event.y
        # If an actor-drag was initiated via Shift, move the actor
        try:
            if getattr(self.app, 'dragging_actor', None):
                new_x = x + getattr(self.app, 'drag_offset_x', 0)
                # clamp into canvas width
                new_x = max(ACTOR_WIDTH//2 + 10, min(self.canvas.winfo_width() - ACTOR_WIDTH//2 - 10, new_x))
                self.app.dragging_actor.x = new_x
                self.redraw()
                return
        except Exception:
            pass

        # If we previously pressed on an actor and moved more than threshold, start interaction drag
        if self.pressed_actor and not self.dragging_interaction:
            dx = x - (self.press_x or 0)
            dy = y - (self.press_y or 0)
            if hypot(dx, dy) >= self._drag_threshold:
                # begin interaction drag from pressed actor
                self.dragging_interaction = True
                try:
                    self.app.interaction_start_actor = self.pressed_actor
                except Exception:
                    self.app.interaction_start_actor = None

        # If we are in interaction-drag mode (either because the checkbox was enabled, or we started one here)
        if self.dragging_interaction or (self.app.creating_interaction and self.app.interaction_start_actor):
            # draw temporary line from start actor center to current mouse
            start_actor = self.app.interaction_start_actor
            if not start_actor:
                return
            sx = start_actor.x
            sy = INTERACTION_START_Y
            if self.app.temp_line:
                try:
                    self.canvas.delete(self.app.temp_line)
                except Exception:
                    pass
            # preview style should match selected new-interaction style
            dash = None
            try:
                style = self.app.new_interaction_style.get()
            except Exception:
                style = 'solid'
            if style == 'dashed':
                dash = (6, 4)
            self.app.temp_line = self.canvas.create_line(sx, sy, x, y, arrow=tk.LAST, dash=dash, fill=self.app.palette.get('preview_line'))
            return

        # Previously the app allowed dragging actors; per new behavior we don't start actor drag here.
        # If needed later we can add a modifier key to re-enable actor dragging.

    def on_canvas_release(self, event):
        x, y = event.x, event.y
        # If we were dragging an actor (Shift-drag), stop moving
        try:
            if getattr(self.app, 'dragging_actor', None):
                self.app.dragging_actor = None
                self.app.drag_offset_x = 0
                # reset transient press state
                self.pressed_actor = None
                self.press_x = None
                self.press_y = None
                return
        except Exception:
            pass

        # If we were dragging to create an interaction (started from a press)
        if self.dragging_interaction or (self.app.creating_interaction and self.app.interaction_start_actor):
            # determine which actor (if any) we released over
            target = self.find_actor_at(x, y)
            start_actor = self.app.interaction_start_actor
            if not target or not start_actor:
                try:
                    self.app.dialogs.info("Invalid", "Release on an actor to create an interaction")
                except Exception:
                    pass
            else:
                # create interaction then prompt for a label
                self.app.add_interaction(start_actor, target, label="")
                # prompt user for a label immediately
                try:
                    idx = len(self.app.interactions) - 1
                    new_label = self.app.dialogs.ask_string("Interaction label", "Enter label for this interaction:", parent=self.app.root)
                    if new_label is not None:
                        self.app.interactions[idx].label = new_label
                        self.app.interaction_manager.update_interaction_listbox()
                        self.redraw()
                except Exception:
                    pass
            # cleanup
            self.dragging_interaction = False
            try:
                if self.app.temp_line:
                    self.canvas.delete(self.app.temp_line)
            except Exception:
                pass
            self.app.temp_line = None
            self.app.interaction_start_actor = None
            self.pressed_actor = None
            self.press_x = None
            self.press_y = None
            return

        # If we pressed on an actor but did not move enough to start a drag -> treat as click (select actor)
        if self.pressed_actor:
            try:
                self.app.selected_actor_id = self.pressed_actor.id
                # clear any interaction selection
                try:
                    self.app.interaction_listbox.select_clear(0, tk.END)
                    try:
                        self.app.style_menu.configure(state='disabled')
                    except Exception:
                        pass
                except Exception:
                    pass
                self.redraw()
            except Exception:
                pass

        # Reset transient press state
        self.pressed_actor = None
        self.press_x = None
        self.press_y = None

    # Drawing
    def redraw(self):
        self.canvas.delete("all")
        # draw actors
        for actor in self.app.actors:
            left = actor.x - ACTOR_WIDTH // 2
            top = actor.y
            right = actor.x + ACTOR_WIDTH // 2
            bottom = actor.y + ACTOR_HEIGHT
            # if actor is selected, draw an accent outline behind it
            try:
                if getattr(self.app, 'selected_actor_id', None) == actor.id:
                    # slightly larger rect for outline
                    outline_margin = 3
                    self.canvas.create_rectangle(left - outline_margin, top - outline_margin, right + outline_margin, bottom + outline_margin, outline=self.app.palette.get('accent', '#4a90e2'), width=3)
            except Exception:
                pass
            actor.rect_id = self.canvas.create_rectangle(left, top, right, bottom, fill=self.app.palette.get('actor_fill', '#f0f0ff'), outline=self.app.palette.get('actor_outline', '#000'))
            actor.text_id = self.canvas.create_text(actor.x, actor.y + ACTOR_HEIGHT//2, text=actor.name, fill=self.app.palette.get('actor_text'))
            # lifeline (dashed)
            lx = actor.x
            ly1 = bottom
            ly2 = CANVAS_HEIGHT - 20
            self.canvas.create_line(lx, ly1, lx, ly2, dash=(4,4), fill=self.app.palette.get('lifeline', '#888'))

        # determine currently selected interaction index (if any) from listbox
        try:
            sel = self.app.interaction_listbox.curselection()
            selected_idx = sel[0] if sel else None
        except Exception:
            selected_idx = None

        # draw interactions in order
        for i, inter in enumerate(self.app.interactions):
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

            is_selected = (i == selected_idx)
            # if selected, draw a thicker outline line behind the normal line
            if is_selected:
                outline_color = self.app.palette.get('accent', '#4a90e2')
                try:
                    # wider outline line (drawn first so main line sits on top)
                    self.canvas.create_line(sx, y, tx, y, arrow=tk.LAST, width=6, dash=dash, fill=outline_color, tags=(f"interaction_{i}",))
                except Exception:
                    pass

            line_color = self.app.palette.get('label_fg')
            line = self.canvas.create_line(sx, y, tx, y, arrow=tk.LAST, width=2, dash=dash, fill=line_color, tags=(f"interaction_{i}",))
            # label and index
            midx = (sx + tx) // 2
            self.canvas.create_text(midx, y - 10, text=inter.label, fill=self.app.palette.get('label_fg'), tags=(f"interaction_label_{i}", f"interaction_{i}"))
            self.canvas.create_text(40, y, text=str(i+1), fill=self.app.palette.get('index_fg'))
            # bind canvas events for selection and editing (single-click selects, double-click edits label)
            try:
                self.canvas.tag_bind(f"interaction_{i}", "<Button-1>", lambda e, ii=i: self.app.interaction_manager.select_interaction(ii))
                self.canvas.tag_bind(f"interaction_{i}", "<Double-Button-1>", lambda e, ii=i: self.app.interaction_manager.edit_interaction_label_at(ii))
            except Exception:
                pass

        # NOTE: removed the call to update_interaction_listbox() here to avoid a redraw -> listbox update -> redraw recursion
