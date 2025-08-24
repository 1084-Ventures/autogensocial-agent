import azure.functions as func
import base64
import logging
from io import BytesIO
from typing import Optional, List, Dict, Any
from PIL import Image, ImageDraw, ImageFont
import requests

bp = func.Blueprint()

@bp.route(route="compose_image")
@bp.function_name(name="compose_image")
def compose_image_handler(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing compose image request')
    try:
        req_body = req.get_json()
        size = req_body.get("size")
        background_color = req_body.get("background_color")
        base_image_url = req_body.get("base_image_url")
        text_elements = req_body.get("text_elements")
        image_overlays = req_body.get("image_overlays")
        additional_params = req_body.get("additional_params")
        img = compose_image(
            size=size,
            background_color=background_color,
            base_image_url=base_image_url,
            text_elements=text_elements,
            image_overlays=image_overlays,
            additional_params=additional_params
        )
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        img_bytes = buf.read()
        return func.HttpResponse(
            img_bytes,
            status_code=200,
            mimetype="image/png"
        )
    except Exception as e:
        return func.HttpResponse(
            f"Error: {str(e)}",
            status_code=400
        )


def parse_size(size_str: Optional[str]) -> tuple:
    if size_str:
        try:
            width, height = map(int, size_str.lower().split('x'))
            return width, height
        except Exception:
            pass
    return 1024, 1024  # Default size


def compose_image(
    size: Optional[str] = None,
    background_color: Optional[str] = None,
    base_image_url: Optional[str] = None,
    text_elements: Optional[List[Dict[str, Any]]] = None,
    image_overlays: Optional[List[Dict[str, Any]]] = None,
    additional_params: Optional[Dict[str, Any]] = None
) -> Image.Image:
    """
    Compose an image using Pillow based on the flexible contract.
    Returns a Pillow Image object.
    """
    width, height = parse_size(size)
    bg_color = background_color or "white"

    # Start from base image or blank
    if base_image_url:
        try:
            response = requests.get(base_image_url)
            image = Image.open(BytesIO(response.content)).convert("RGBA")
            image = image.resize((width, height))
        except Exception:
            image = Image.new("RGBA", (width, height), color=bg_color)
    else:
        image = Image.new("RGBA", (width, height), color=bg_color)
    draw = ImageDraw.Draw(image)

    # Draw text elements
    if text_elements:
        for elem in text_elements:
            text = elem.get("text", "")
            position = tuple(elem.get("position", (0, 0)))
            color = elem.get("color", "black")
            font_path = elem.get("font")
            size = elem.get("size", 40)
            anchor = elem.get("anchor", None)
            try:
                fnt = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
            except Exception:
                fnt = ImageFont.load_default()
            draw.text(position, text, font=fnt, fill=color, anchor=anchor)

    # Draw image overlays
    if image_overlays:
        for overlay in image_overlays:
            try:
                response = requests.get(overlay["image_url"])
                overlay_img = Image.open(BytesIO(response.content)).convert("RGBA")
                if overlay.get("size"):
                    overlay_img = overlay_img.resize(tuple(overlay["size"]))
                opacity = overlay.get("opacity")
                if opacity is not None:
                    alpha = overlay_img.split()[3]
                    alpha = alpha.point(lambda p: int(p * opacity))
                    overlay_img.putalpha(alpha)
                pos = tuple(overlay.get("position", (0, 0)))
                image.paste(overlay_img, pos, overlay_img)
            except Exception:
                pass

    # Additional params (e.g., filters)
    if additional_params:
        if additional_params.get("grayscale"):
            image = image.convert("L").convert("RGBA")
        # Add more custom manipulations as needed

    return image.convert("RGB")
