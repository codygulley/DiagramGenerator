"""InteractionManager: handles the interactions listbox and related actions.

This module is a thin wrapper that manipulates the `app.interactions` list and updates
UI widgets owned by the app.
"""
import tkinter as tk


class InteractionManager:
    def __init__(self, app):
        self.app = app
        self.listbox = app.interaction_listbox

    def update_interaction_listbox(self, selected_idx_override: int = None):
        """Rebuild the listbox contents.

        If `selected_idx_override` is provided, that index will be selected after
        rebuilding (if it's in range). Otherwise the previously selected index is
        restored when possible.
        """
        # preserve current selection index
        try:
            cur_sel = self.listbox.curselection()
            cur_idx = cur_sel[0] if cur_sel else None
        except Exception:
            cur_idx = None

        # prefer explicit override when provided
        if selected_idx_override is not None:
            target_idx = selected_idx_override
        else:
            target_idx = cur_idx

        self.listbox.delete(0, tk.END)
        for i, inter in enumerate(self.app.interactions):
            src = self.app.get_actor_by_id(inter.source_id)
            tgt = self.app.get_actor_by_id(inter.target_id)
            src_name = src.name if src else f"id:{inter.source_id}"
            tgt_name = tgt.name if tgt else f"id:{inter.target_id}"
            s = f"{i+1}. {src_name} -> {tgt_name} [{inter.style}]: {inter.label}"
            self.listbox.insert(tk.END, s)

        # restore/establish selection if possible
        if target_idx is not None and 0 <= target_idx < len(self.app.interactions):
            try:
                # clear any previous selection and set the intended one exactly once
                try:
                    self.listbox.select_clear(0, tk.END)
                except Exception:
                    pass
                self.listbox.select_set(target_idx)
                # make sure dropdown & canvas reflect selection
                self.on_interaction_select()
            except Exception:
                pass
        else:
            # No valid selection: disable style/menu and action buttons
            try:
                if hasattr(self.app, 'style_menu'):
                    self.app.style_menu.configure(state='disabled')
            except Exception:
                pass
            try:
                if hasattr(self.app, 'up_btn'):
                    self.app.up_btn.configure(state='disabled')
                if hasattr(self.app, 'down_btn'):
                    self.app.down_btn.configure(state='disabled')
                if hasattr(self.app, 'edit_btn'):
                    self.app.edit_btn.configure(state='disabled')
                if hasattr(self.app, 'delete_btn'):
                    self.app.delete_btn.configure(state='disabled')
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

    def deselect_all(self):
        """Clear any selection and update UI state (disables buttons/menus)."""
        try:
            self.listbox.select_clear(0, tk.END)
        except Exception:
            pass
        try:
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
        # keep the same item selected after update
        self.update_interaction_listbox(selected_idx_override=idx)
        self.app.canvas_controller.redraw()

    def on_interaction_select(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            try:
                if hasattr(self.app, 'style_menu'):
                    self.app.style_menu.configure(state='disabled')
            except Exception:
                pass
            # disable action buttons
            try:
                if hasattr(self.app, 'up_btn'):
                    self.app.up_btn.configure(state='disabled')
                if hasattr(self.app, 'down_btn'):
                    self.app.down_btn.configure(state='disabled')
                if hasattr(self.app, 'edit_btn'):
                    self.app.edit_btn.configure(state='disabled')
                if hasattr(self.app, 'delete_btn'):
                    self.app.delete_btn.configure(state='disabled')
            except Exception:
                pass
            # redraw to clear any selection highlight
            try:
                self.app.canvas_controller.redraw()
            except Exception:
                pass
            return
        idx = sel[0]
        # clear actor selection when an interaction is selected
        try:
            self.app.selected_actor_id = None
        except Exception:
            pass
        inter = self.app.interactions[idx]
        try:
            self.app.style_var.set(inter.style)
            try:
                self.app.style_menu.configure(state='normal')
            except Exception:
                pass
            # enable action buttons
            try:
                if hasattr(self.app, 'up_btn'):
                    self.app.up_btn.configure(state='normal')
                if hasattr(self.app, 'down_btn'):
                    self.app.down_btn.configure(state='normal')
                if hasattr(self.app, 'edit_btn'):
                    self.app.edit_btn.configure(state='normal')
                if hasattr(self.app, 'delete_btn'):
                    self.app.delete_btn.configure(state='normal')
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
            # keep selection stable
            self.update_interaction_listbox(selected_idx_override=idx)
            self.app.canvas_controller.redraw()

    def move_interaction_up(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx == 0:
            return
        self.app.interactions[idx-1], self.app.interactions[idx] = self.app.interactions[idx], self.app.interactions[idx-1]
        # update list and select new (moved) index
        self.update_interaction_listbox(selected_idx_override=idx-1)
        self.app.canvas_controller.redraw()

    def move_interaction_down(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(self.app.interactions)-1:
            return
        self.app.interactions[idx+1], self.app.interactions[idx] = self.app.interactions[idx], self.app.interactions[idx+1]
        # update list and select new (moved) index
        self.update_interaction_listbox(selected_idx_override=idx+1)
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
        # keep same item selected
        self.update_interaction_listbox(selected_idx_override=idx)
        self.app.canvas_controller.redraw()

    def delete_interaction(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        del self.app.interactions[idx]
        # after deletion, select the next item if any, or the previous one
        new_sel = None
        if idx < len(self.app.interactions):
            new_sel = idx
        elif len(self.app.interactions) > 0:
            new_sel = len(self.app.interactions) - 1
        self.update_interaction_listbox(selected_idx_override=new_sel)
        self.app.canvas_controller.redraw()
