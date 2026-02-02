import tempfile
import os
import shutil
from typing import Optional, Tuple

try:
    from PIL import Image, ImageGrab
except Exception:
    try:
        from PIL import Image
        ImageGrab = None
    except Exception:
        Image = None
        ImageGrab = None


def find_ghostscript() -> Optional[str]:
    """Return path to ghostscript executable if found, else None."""
    candidates = ["gswin64c", "gswin32c", "gs"]
    for name in candidates:
        p = shutil.which(name)
        if p:
            return p
    return None


def postscript_to_image(ps_path: str) -> 'Image.Image':
    """Open a PostScript file via Pillow. Raises if Pillow not available or open fails."""
    if Image is None:
        raise RuntimeError('Pillow (PIL) is required')
    img = Image.open(ps_path)
    return img


def chroma_key_transparent(img, bg_rgb: Tuple[int,int,int], tol: int = 10):
    """Make pixels matching bg_rgb (within tol) transparent and return a new Image."""
    if Image is None:
        raise RuntimeError('Pillow (PIL) is required')
    img = img.convert('RGBA')
    datas = img.getdata()
    newData = []
    for item in datas:
        r, g, b, a = item
        if (abs(r - bg_rgb[0]) <= tol and abs(g - bg_rgb[1]) <= tol and abs(b - bg_rgb[2]) <= tol):
            newData.append((r, g, b, 0))
        else:
            newData.append((r, g, b, a))
    img.putdata(newData)
    return img


def save_image(img, out_path: str):
    if Image is None:
        raise RuntimeError('Pillow (PIL) is required')
    img.save(out_path)
    return out_path


def export_canvas(canvas, root, out_path: str, transparent: bool = False) -> str:
    """Export a Tkinter canvas to out_path. Raises RuntimeError on failure.

    Tries PostScript -> Pillow (requires Ghostscript for correct colors) first,
    then falls back to ImageGrab if available.
    """
    gs_path = find_ghostscript()
    if gs_path is None and ImageGrab is None:
        raise RuntimeError("PostScript export requires Ghostscript and Pillow. Ghostscript not found and ImageGrab fallback is not available.")

    ps_path = None
    last_exc = None
    try:
        # PostScript route
        try:
            canvas.update()
            with tempfile.NamedTemporaryFile(delete=False, suffix='.ps') as tmp:
                ps_path = tmp.name
            canvas.postscript(file=ps_path, colormode='color')
            img = postscript_to_image(ps_path)
            if out_path.lower().endswith(('.jpg', '.jpeg')):
                img = img.convert('RGB')
            else:
                img = img.convert('RGBA')

            if out_path.lower().endswith('.png') and transparent:
                try:
                    bg = canvas.cget('bg')
                    r16, g16, b16 = root.winfo_rgb(bg)
                    bg_rgb = (r16 // 256, g16 // 256, b16 // 256)
                except Exception:
                    bg_rgb = (255, 255, 255)
                img = chroma_key_transparent(img, bg_rgb)

            save_image(img, out_path)
            return out_path
        except Exception as e:
            last_exc = e

        # ImageGrab fallback
        if ImageGrab is not None:
            try:
                canvas.update()
                x = canvas.winfo_rootx()
                y = canvas.winfo_rooty()
                w = canvas.winfo_width()
                h = canvas.winfo_height()
                bbox = (x, y, x + w, y + h)
                img = ImageGrab.grab(bbox)
                if out_path.lower().endswith(('.jpg', '.jpeg')):
                    img = img.convert('RGB')
                else:
                    img = img.convert('RGBA')

                if out_path.lower().endswith('.png') and transparent:
                    try:
                        bg = canvas.cget('bg')
                        r16, g16, b16 = root.winfo_rgb(bg)
                        bg_rgb = (r16 // 256, g16 // 256, b16 // 256)
                    except Exception:
                        bg_rgb = (255, 255, 255)
                    img = chroma_key_transparent(img, bg_rgb)

                save_image(img, out_path)
                return out_path
            except Exception as e2:
                last_exc = (last_exc, e2)
                raise

        raise RuntimeError("PostScript export failed and ImageGrab fallback is not available")
    except Exception as final_exc:
        msg = "Export failed."
        if isinstance(last_exc, tuple):
            msg += f"\nPostScript error: {last_exc[0]}\nImageGrab error: {last_exc[1]}"
        else:
            msg += f"\nError: {last_exc or final_exc}"
        raise RuntimeError(msg)
    finally:
        try:
            if ps_path and os.path.exists(ps_path):
                os.remove(ps_path)
        except Exception:
            pass
