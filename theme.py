"""Theme palettes and helper constants used by the app.

This module centralizes the light and dark palettes used by the UI. Export a simple
helper `palette_for_theme(name)` which returns a copy of the requested palette.
"""

LIGHT_PALETTE = {
    'app_bg': '#f5f7fa',
    'card_bg': '#ffffff',
    'text_fg': '#111827',
    'muted_fg': '#6b7280',
    'accent': '#4a90e2',
    'card_border': '#e6e9ef',
    'canvas_bg': '#ffffff',
    'actor_text': '#111111',
    'label_fg': '#222222',
    'index_fg': '#666666',
    'preview_line': '#999999',
    'actor_fill': '#f0f0ff',
    'actor_outline': '#000000',
    'lifeline': '#888888'
}

DARK_PALETTE = {
    'app_bg': '#111217',
    'card_bg': '#111217',
    'text_fg': '#e6eef6',
    'muted_fg': '#9aa3ad',
    'accent': '#4a90e2',
    'card_border': '#0b1116',
    'canvas_bg': '#111217',
    'actor_fill': '#181b22',
    'actor_outline': '#262a31',
    'actor_text': '#e6eef6',
    'label_fg': '#e6eef6',
    'index_fg': '#9aa3ad',
    'preview_line': '#6b7280',
    'lifeline': '#2f3440'
}


def palette_for_theme(name: str):
    """Return a copy of the palette for the given theme name ('light' or 'dark').

    If `name` is falsy or not recognized, the light palette is returned.
    """
    if not name:
        return LIGHT_PALETTE.copy()
    n = name.lower()
    if n == 'dark':
        return DARK_PALETTE.copy()
    return LIGHT_PALETTE.copy()
