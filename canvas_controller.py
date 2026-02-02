"""CanvasController: handles canvas drawing and mouse interactions.

This module is intentionally independent from `diagram_app` to avoid circular imports; it
receives the `app` instance (DiagramApp) and reads/writes state on it.
"""
import tkinter as tk
from typing import Optional
from models import ACTOR_WIDTH, ACTOR_HEIGHT, INTERACTION_START_Y, INTERACTION_V_GAP, CANVAS_HEIGHT
from models import Actor


class CanvasController:
    def __init__(self, app):
        self.app = app
        self.canvas = app.canvas

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
        if actor and not self.app.creating_interaction:
            # start dragging actor
            self.app.dragging_actor = actor
            self.app.drag_offset_x = actor.x - x
        elif actor and self.app.creating_interaction:
            # start interaction from this actor
            self.app.interaction_start_actor = actor
        else:
            # click on blank area - deselect
            self.app.dragging_actor = None

    def on_canvas_drag(self, event):
        x, y = event.x, event.y
        if self.app.dragging_actor:
            # move actor horizontally
            new_x = x + self.app.drag_offset_x
            # clamp into canvas
            new_x = max(ACTOR_WIDTH//2 + 10, min(self.canvas.winfo_width() - ACTOR_WIDTH//2 - 10, new_x))
            self.app.dragging_actor.x = new_x
            self.redraw()
        elif self.app.creating_interaction and self.app.interaction_start_actor:
            # draw temporary line from start actor center to current mouse
            sx = self.app.interaction_start_actor.x
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

    def on_canvas_release(self, event):
        x, y = event.x, event.y
        if self.app.dragging_actor:
            self.app.dragging_actor = None
            return
        if self.app.creating_interaction and self.app.interaction_start_actor:
            target = self.find_actor_at(x, y)
            if not target:
                try:
                    self.app.dialogs.info("Invalid", "Release on an actor to create an interaction")
                except Exception:
                    pass
            else:
                # create interaction then prompt for a label
                self.app.add_interaction(self.app.interaction_start_actor, target, label="")
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
            self.app.interaction_start_actor = None
            if self.app.temp_line:
                try:
                    self.canvas.delete(self.app.temp_line)
                except Exception:
                    pass
                self.app.temp_line = None

    # Drawing
    def redraw(self):
        self.canvas.delete("all")
        # draw actors
        for actor in self.app.actors:
            left = actor.x - ACTOR_WIDTH // 2
            top = actor.y
            right = actor.x + ACTOR_WIDTH // 2
            bottom = actor.y + ACTOR_HEIGHT
            actor.rect_id = self.canvas.create_rectangle(left, top, right, bottom, fill=self.app.palette.get('actor_fill', '#f0f0ff'), outline=self.app.palette.get('actor_outline', '#000'))
            actor.text_id = self.canvas.create_text(actor.x, actor.y + ACTOR_HEIGHT//2, text=actor.name, fill=self.app.palette.get('actor_text'))
            # lifeline (dashed)
            lx = actor.x
            ly1 = bottom
            ly2 = CANVAS_HEIGHT - 20
            self.canvas.create_line(lx, ly1, lx, ly2, dash=(4,4), fill=self.app.palette.get('lifeline', '#888'))

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

        # update listbox (ensure selection remains valid)
        self.app.interaction_manager.update_interaction_listbox()


