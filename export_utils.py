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

