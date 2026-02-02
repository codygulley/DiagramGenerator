"""InteractionManager: handles the interactions listbox and related actions.

This module is a thin wrapper that manipulates the `app.interactions` list and updates
UI widgets owned by the app.
"""
import tkinter as tk


class InteractionManager:
    def __init__(self, app):
        self.app = app
        self.listbox = app.interaction_listbox

    def update_interaction_listbox(self):
        # preserve current selection index
        try:
            cur_sel = self.listbox.curselection()
            cur_idx = cur_sel[0] if cur_sel else None
        except Exception:
            cur_idx = None

        self.listbox.delete(0, tk.END)
        for i, inter in enumerate(self.app.interactions):
            src = self.app.get_actor_by_id(inter.source_id)
            tgt = self.app.get_actor_by_id(inter.target_id)
            src_name = src.name if src else f"id:{inter.source_id}"
            tgt_name = tgt.name if tgt else f"id:{inter.target_id}"
            s = f"{i+1}. {src_name} -> {tgt_name} [{inter.style}]: {inter.label}"
            self.listbox.insert(tk.END, s)

        # restore selection if possible
        if cur_idx is not None and 0 <= cur_idx < len(self.app.interactions):
            try:
                self.listbox.select_set(cur_idx)
                # make sure dropdown reflects selection
                self.on_interaction_select()
            except Exception:
                pass

    def select_interaction(self, idx: int):
        try:
            self.listbox.select_clear(0, tk.END)
            self.listbox.select_set(idx)
            self.listbox.see(idx)
            self.on_interaction_select()
        except Exception:
            pass

    def edit_interaction_label_at(self, idx: int):
        if idx < 0 or idx >= len(self.app.interactions):
            return
        inter = self.app.interactions[idx]
        new_label = self.app.dialogs.ask_string("Edit label", "Enter new label:", initial=inter.label, parent=self.app.root)
        if new_label is None:
            return
        inter.label = new_label
        self.update_interaction_listbox()
        self.app.canvas_controller.redraw()

    def on_interaction_select(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            try:
                self.app.style_menu.configure(state='disabled')
            except Exception:
                pass
            # redraw to clear any selection highlight
            try:
                self.app.canvas_controller.redraw()
            except Exception:
                pass
            return
        idx = sel[0]
        inter = self.app.interactions[idx]
        try:
            self.app.style_var.set(inter.style)
            try:
                self.app.style_menu.configure(state='normal')
            except Exception:
                pass
        except Exception:
            pass
        # redraw canvas so the selected interaction shows highlighted outline
        try:
            self.app.canvas_controller.redraw()
        except Exception:
            pass

    def on_style_change(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < 0 or idx >= len(self.app.interactions):
            return
        new_style = self.app.style_var.get()
        inter = self.app.interactions[idx]
        if inter.style != new_style:
            inter.style = new_style
            self.update_interaction_listbox()
            self.app.canvas_controller.redraw()

    def move_interaction_up(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx == 0:
            return
        self.app.interactions[idx-1], self.app.interactions[idx] = self.app.interactions[idx], self.app.interactions[idx-1]
        self.update_interaction_listbox()
        # ensure only the intended item is selected (clear any previous selection first)
        try:
            self.listbox.select_clear(0, tk.END)
        except Exception:
            pass
        self.listbox.select_set(idx-1)
        self.app.canvas_controller.redraw()

    def move_interaction_down(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.app.interactions)-1:
            return
        self.app.interactions[idx+1], self.app.interactions[idx] = self.app.interactions[idx], self.app.interactions[idx+1]
        self.update_interaction_listbox()
        # ensure only the intended item is selected (clear any previous selection first)
        try:
            self.listbox.select_clear(0, tk.END)
        except Exception:
            pass
        self.listbox.select_set(idx+1)
        self.app.canvas_controller.redraw()

    def edit_interaction_label(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        inter = self.app.interactions[idx]
        new_label = self.app.dialogs.ask_string("Edit label", "Enter new label:", initial=inter.label)
        if new_label is None:
            return
        inter.label = new_label
        self.update_interaction_listbox()
        self.app.canvas_controller.redraw()

    def delete_interaction(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        del self.app.interactions[idx]
        self.update_interaction_listbox()
        self.app.canvas_controller.redraw()
