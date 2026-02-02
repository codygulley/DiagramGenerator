"""Small UI helpers for window placement.

Provides center_window(window, parent) which positions a Toplevel or window
centered over the parent window (or the screen if parent is None).
"""
from typing import Optional


def center_window(win, parent: Optional[object] = None):
    """Center `win` (a tk.Toplevel or tk.Tk) over `parent`.

    The function is defensive: it calls update_idletasks() to ensure geometry
    measurements are available, falls back to screen centering if parent has
    zero size, and ensures the calculated position is non-negative.
    """
    try:
        # Ensure sizes are computed
        win.update_idletasks()
        if parent is None:
            try:
                parent = win.master
            except Exception:
                parent = None

        # Get window size
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()

        # Parent geometry
        if parent is not None:
            try:
                parent.update_idletasks()
                px = parent.winfo_rootx()
                py = parent.winfo_rooty()
                pw = parent.winfo_width()
                ph = parent.winfo_height()
                # If parent reports zero size, fall back to screen
                if pw <= 1 or ph <= 1:
                    parent = None
            except Exception:
                parent = None

        if parent is None:
            sw = win.winfo_screenwidth()
            sh = win.winfo_screenheight()
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2)
        else:
            x = max(0, px + (pw - w) // 2)
            y = max(0, py + (ph - h) // 2)

        win.geometry(f"+{x}+{y}")
    except Exception:
        try:
            # Best-effort fallback: center on screen
            sw = win.winfo_screenwidth()
            sh = win.winfo_screenheight()
            win.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")
        except Exception:
            pass
