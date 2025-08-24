"""
Image generation tool for creating social media images
"""
from typing import Dict, Any, Optional, List

from PIL import Image, ImageDraw, ImageFont
import io
import base64
import logging
import requests
from io import BytesIO

# Tool definition


def generate_social_image(
    size: Optional[str] = None,
    background_color: Optional[str] = None,
    base_image_url: Optional[str] = None,
    text_elements: Optional[List[Dict[str, Any]]] = None,
    image_overlays: Optional[List[Dict[str, Any]]] = None,
    additional_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate a social media image with the specified parameters.
    Args:
        size (str, optional): Image dimensions in WxH format
        background_color (str, optional): Background color
        base_image_url (str, optional): URL of base image
        text_elements (List[Dict], optional): Text to add to image
        image_overlays (List[Dict], optional): Images to overlay
        additional_params (Dict, optional): Additional parameters
    Returns:
        Dict[str, Any]: Generated image data and metadata
    """
    try:
        # Parse size
        width, height = 1024, 1024  # Default size
        if size:
            try:
                width, height = map(int, size.lower().split('x'))
            except ValueError:
                logging.warning(f"Invalid size format: {size}, using default")
        # Create base image
        bg_color = background_color or "white"
        if base_image_url:
            try:
                response = requests.get(base_image_url)
                image = Image.open(BytesIO(response.content)).convert("RGBA")
                image = image.resize((width, height))
            except Exception as e:
                logging.error(f"Error loading base image: {str(e)}")
                image = Image.new("RGBA", (width, height), color=bg_color)
        else:
            image = Image.new("RGBA", (width, height), color=bg_color)
        draw = ImageDraw.Draw(image)
        # Add text elements
        if text_elements:
            for elem in text_elements:
                text = elem.get("text", "")
                position = tuple(elem.get("position", (0, 0)))
                color = elem.get("color", "black")
                font_path = elem.get("font")
                size = elem.get("size", 40)
                try:
                    font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
                except Exception:
                    font = ImageFont.load_default()
                draw.text(position, text, fill=color, font=font)
        # Add image overlays
        if image_overlays:
            for overlay in image_overlays:
                overlay_url = overlay.get("url")
                position = tuple(overlay.get("position", (0, 0)))
                try:
                    response = requests.get(overlay_url)
                    overlay_img = Image.open(BytesIO(response.content)).convert("RGBA")
                    image.paste(overlay_img, position, overlay_img)
                except Exception as e:
                    logging.error(f"Error loading overlay image: {str(e)}")
        # Apply additional params (filters, etc.) if needed
        # ... (custom logic can be added here)
        # Convert to base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return {
            "success": True,
            "image_data": img_str,
            "format": "PNG",
            "encoding": "base64",
            "size": f"{width}x{height}",
            "status": "completed"
        }
    except Exception as e:
        error_msg = f"Error generating image: {str(e)}"
        logging.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }

image_generator_tool = {
    "name": "generate_social_image",
    "description": "Generate a social media image based on provided parameters",
    "parameters": {
        "size": {"type": "string", "description": "Image size in format WxH"},
        "background_color": {"type": "string", "description": "Background color name or hex code"},
        "base_image_url": {"type": "string", "description": "Optional URL of base image to use"},
        "text_elements": {"type": "array", "description": "List of text elements to add to the image"},
        "image_overlays": {"type": "array", "description": "List of image overlays to add"},
        "additional_params": {"type": "object", "description": "Additional parameters like filters"}
    },
    "implementation": generate_social_image
}

def generate_social_image(
    size: Optional[str] = None,
    background_color: Optional[str] = None,
    base_image_url: Optional[str] = None,
    text_elements: Optional[List[Dict[str, Any]]] = None,
    image_overlays: Optional[List[Dict[str, Any]]] = None,
    additional_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate a social media image with the specified parameters.
    
    Args:
        size (str, optional): Image dimensions in WxH format
        background_color (str, optional): Background color
        base_image_url (str, optional): URL of base image
        text_elements (List[Dict], optional): Text to add to image
        image_overlays (List[Dict], optional): Images to overlay
        additional_params (Dict, optional): Additional parameters
        
    Returns:
        Dict[str, Any]: Generated image data and metadata
    """
    try:
        # Parse size
        width, height = 1024, 1024  # Default size
        if size:
            try:
                width, height = map(int, size.lower().split('x'))
            except ValueError:
                logging.warning(f"Invalid size format: {size}, using default")
                
        # Create base image
        bg_color = background_color or "white"
        if base_image_url:
            try:
                response = requests.get(base_image_url)
                image = Image.open(BytesIO(response.content)).convert("RGBA")
                image = image.resize((width, height))
            except Exception as e:
                logging.error(f"Error loading base image: {str(e)}")
                image = Image.new("RGBA", (width, height), color=bg_color)
        else:
            image = Image.new("RGBA", (width, height), color=bg_color)
            
        draw = ImageDraw.Draw(image)
        
        # Add text elements
        if text_elements:
            for elem in text_elements:
                text = elem.get("text", "")
                position = tuple(elem.get("position", (0, 0)))
                color = elem.get("color", "black")
                font_path = elem.get("font")
                size = elem.get("size", 40)
                anchor = elem.get("anchor", None)
                
                try:
                    font = ImageFont.truetype(font_path, size) if font_path else ImageFont.load_default()
                except Exception:
                    font = ImageFont.load_default()
                    
                draw.text(position, text, font=font, fill=color, anchor=anchor)
                
        # Add image overlays
        if image_overlays:
            for overlay in image_overlays:
                try:
                    response = requests.get(overlay["image_url"])
                    overlay_img = Image.open(BytesIO(response.content)).convert("RGBA")
                    
                    if overlay.get("size"):
                        overlay_img = overlay_img.resize(tuple(overlay["size"]))
                        
                    if overlay.get("opacity") is not None:
                        alpha = overlay_img.split()[3]
                        alpha = alpha.point(lambda p: int(p * overlay["opacity"]))
                        overlay_img.putalpha(alpha)
                        
                    pos = tuple(overlay.get("position", (0, 0)))
                    image.paste(overlay_img, pos, overlay_img)
                except Exception as e:
                    logging.error(f"Error adding overlay: {str(e)}")
                    
        # Apply additional processing
        if additional_params:
            if additional_params.get("grayscale"):
                image = image.convert("L").convert("RGBA")
                
        # Convert to base64
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return {
            "success": True,
            "image_data": img_str,
            "format": "PNG",
            "encoding": "base64",
            "size": f"{width}x{height}",
            "status": "completed"
        }
        
    except Exception as e:
        error_msg = f"Error generating image: {str(e)}"
        logging.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }
        
