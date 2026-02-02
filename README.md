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
- Export to PNG and JPEG. PNG export supports an optional transparency mode (chroma-keying the canvas background).

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
- The `main.py` file is now a tiny launcher that imports and runs the application from `diagram_app.py` (the UI and app logic were split into separate modules for clarity).

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

This project was recently refactored to split responsibilities into smaller modules. High-level layout:

- `main.py` — small launcher (bootstrap). Keeps run configuration simple for IDEs.
- `diagram_app.py` — the main application class (`DiagramApp`) that composes the UI and coordinates components.
- `canvas_controller.py` — `CanvasController` handles canvas drawing and mouse interactions (press/drag/release) and is responsible for rendering actors, lifelines and interactions.
- `interaction_manager.py` — `InteractionManager` handles the interactions listbox and related actions (select, edit label, move up/down, delete).
- `models.py` — dataclasses and layout/constants (Actor, Interaction, sizing and color constants).
- `dialogs.py` — themed modal dialogs (and a simple fallback) used by the app.
- `export_utils.py` — export helpers (ghostscript detection, PostScript -> Pillow flow, ImageGrab fallback, chroma-key transparency).

Developer notes / rationale

- The controllers/managers receive the `app` instance and operate on `app` state rather than importing `DiagramApp`; this avoids circular imports and keeps modules decoupled.
- Export logic is centralized in `export_utils.export_canvas(canvas, root, out_path, transparent)` so UI code stays thin and easier to test.
- UI initialization remains in `diagram_app.py`, but it can be split further into builder functions (left/right panel builders) if desired.

## Troubleshooting

- Add Actor / Label dialogs not showing or errors on theme change: restart the application after code changes. The app loads modules at startup.
- Export errors mentioning Ghostscript: install Ghostscript (https://www.ghostscript.com/) and add it to your PATH, or rely on the ImageGrab fallback by ensuring Pillow supports it and the app window is visible.
- If the UI looks off on your platform (native widgets drawing differently), some widgets intentionally use native dialogs (file save) which will not be themed.

## Running the testable parts (developer hints)

- `export_utils.py` contains pure logic that is easy to unit test. You can write tests that mock a canvas object and Pillow calls.
- `canvas_controller.py` and `interaction_manager.py` are thin wrappers around the GUI state and are best tested by driving small functional tests or by isolating their logic behind interfaces/mocks.

## Roadmap / Future improvements

- Add undo/redo for actor and interaction changes.
- Better alignment/snapping and grid support for actor placement.
- Multi-page/long diagrams with scrolling and scaling.
- Export to SVG and/or direct PlantUML generation.
- Add a small project file format (save/load diagrams as JSON) and tests for export utilities.

## Contributing

Patches, bug reports, and feature requests are welcome. Open an issue describing the problem or a proposal and include a short reproducible example if possible.

## License

This repository is provided without an explicit license. If you plan to reuse or distribute the code, consider adding a license (for example MIT) to clarify terms.