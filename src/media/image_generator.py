import io
import os
from typing import Dict, Tuple

from PIL import Image, ImageDraw, ImageFont


def _wrap_text(text: str, draw: ImageDraw.ImageDraw, max_width: int, font: ImageFont.ImageFont) -> str:
    words = text.split()
    lines = []
    line = ""
    for w in words:
        test = (line + " " + w).strip()
        w_px, _ = draw.textsize(test, font=font)
        if w_px <= max_width or not line:
            line = test
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return "\n".join(lines)


def _pick_font(size: int) -> ImageFont.ImageFont:
    # Try a few common fonts; fallback to default
    for name in [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/SFNS.ttf",
        "/Library/Fonts/Arial.ttf",
    ]:
        try:
            return ImageFont.truetype(name, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def generate_placeholder_image(caption: str, *, size: Tuple[int, int] = (1024, 1024)) -> Tuple[bytes, Dict]:
    """Create a simple placeholder image containing the caption text.

    Returns (png_bytes, metadata)
    """
    img = Image.new("RGB", size, color=(245, 245, 245))
    draw = ImageDraw.Draw(img)
    w, h = size
    title_font = _pick_font(56)
    body_font = _pick_font(32)

    # Title
    title = "AutogenSocial"
    tw, th = draw.textsize(title, font=title_font)
    draw.text(((w - tw) / 2, 60), title, fill=(30, 30, 30), font=title_font)

    # Caption box
    margin = 80
    max_text_width = w - margin * 2
    wrapped = _wrap_text(caption.strip(), draw, max_text_width, body_font)
    # Draw caption centered block
    _, line_h = draw.textsize("Ag", font=body_font)
    lines = wrapped.splitlines() if wrapped else []
    block_h = len(lines) * (line_h + 8)
    y = (h - block_h) / 2
    for line in lines:
        lw, _ = draw.textsize(line, font=body_font)
        draw.text(((w - lw) / 2, y), line, fill=(50, 50, 50), font=body_font)
        y += line_h + 8

    # Footer
    footer = "placeholder image"
    fw, fh = draw.textsize(footer, font=ImageFont.load_default())
    draw.text(((w - fw) / 2, h - fh - 24), footer, fill=(120, 120, 120))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue(), {"provider": "placeholder", "width": w, "height": h}

