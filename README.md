# Diagram Generator

A small desktop application for quickly building simple diagrams — initially focused on sequence diagrams.

This project provides a lightweight WYSIWYG-style editor where you can add actors (systems, APIs, people), drag them horizontally, and create ordered interactions between them by dragging.

The application emphasizes a modern, themable UI and supports exporting the diagram to image formats (PNG/JPEG) with an option for transparent PNG output.

---

## Features

- Add and position actors on a canvas.
- Create interactions by dragging from one actor to another while in "New Interaction" mode.
- Order interactions using the right-hand list (Up / Down) and edit or delete interactions.
- Style interactions as solid or dashed lines.
- Add labels to interactions (visible above the line).
- Dark and light themes; preference saved to a config file and defaults to the OS system theme.
- Modern-themed dialogs for entering actor names and interaction labels.
- Export to PNG and JPEG. PNG export supports a transparency option (chroma-keying the canvas background).

## Quickstart

1. (Optional) Create a virtual environment and activate it:

```bash
python -m venv .venv
# Windows (cmd.exe)
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

2. Install dependencies (Pillow is required for exporting images):

```bash
pip install pillow
```

3. Run the app from the project root:

```bash
python main.py
```

Notes:
- The export functionality uses Pillow. On Windows, if PostScript conversion is used the app may also require Ghostscript for accurate PostScript -> image conversion. If Ghostscript is not found, the app falls back to a screen-capture method (ImageGrab), which requires the app window to be visible on screen.

## Export / Transparency details

- PNG: Supported. If you enable the "Transparent background" option in the export modal, the app will attempt to remove pixels matching the canvas background color.
- JPEG: Supported (no transparency).

Two export routes are attempted (in order):
1. PostScript route: the canvas is exported to a temporary PostScript file and opened with Pillow. On Windows this often requires Ghostscript to be installed and on PATH.
2. ImageGrab fallback: if Ghostscript/Pillow PS support is unavailable, the app will capture a screenshot of the canvas area and save it. This requires Pillow with ImageGrab support and an unobstructed app window.

If you encounter errors that mention Ghostscript, installing Ghostscript and adding it to your PATH is the recommended fix on Windows.

## Configuration & Data

- Preferences (currently theme selection) are saved to a JSON file in the user's config area:
  - Windows: `%APPDATA%\DiagramGenerator\diagram_config.json`
  - macOS / Linux: `~/diagram_config.json` (or `~/.diagram_config.json` as a fallback)

## File / Module layout (high-level)

- `main.py` — main application UI and canvas logic.
- `models.py` — dataclasses and layout constants (Actor, Interaction, sizing constants).
- `dialogs.py` — themed modal dialogs (and a simple fallback) used by the app.
- `export_utils.py` — small helpers for export (Ghostscript detection, chroma-key transparency helpers).

## Troubleshooting

- Add Actor / Label dialogs not showing or errors on theme change: restart the application after code changes. The app loads modules at startup.
- Export errors mentioning Ghostscript: install Ghostscript (https://www.ghostscript.com/) and add it to your PATH, or rely on the ImageGrab fallback by ensuring Pillow supports it.
- If the UI looks off on your platform (native widgets drawing differently), some widgets intentionally use native dialogs (file save) which will not be themed.

## Roadmap / Future improvements

- Move the entire export pipeline into `export_utils.py` and add unit tests for it.
- Add undo/redo for actor and interaction changes.
- Support for lifelines with custom styling and activation boxes.
- Better alignment/snapping and grid support for actor placement.
- Multi-page/long diagrams with scrolling and scaling.
- Export to SVG and/or direct PlantUML generation.
- Add a small project file format (save/load diagrams as JSON).

## Contributing

Patches, bug reports, and feature requests are welcome. Open an issue describing the problem or a proposal and include a short reproducible example if possible.

## License

This repository is provided without an explicit license. If you plan to reuse or distribute the code, consider adding a license (for example MIT) to clarify terms.