"""
Tool for processing image generation tasks
"""
import logging
from typing import Dict, Any, Optional, List
from src.function_blueprints.compose_image_blueprint import compose_image
from PIL import Image
import io
import base64

def process_image_task_tool(
    run_trace_id: str,
    image_params: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process an image generation task with the given parameters.
    
    Args:
        run_trace_id (str): The trace ID for tracking
        image_params (Dict[str, Any]): The image generation parameters
        
    Returns:
        Dict[str, Any]: The generation result including the image data
    """
    logging.info(f"Processing image generation task - Trace ID: {run_trace_id}")
    
    if not image_params:
        raise ValueError("Image parameters are required")
    
    # Generate image
    img = compose_image(
        size=image_params.get('size'),
        background_color=image_params.get('backgroundColor'),
        base_image_url=image_params.get('baseImageUrl'),
        text_elements=image_params.get('textElements'),
        image_overlays=image_params.get('imageOverlays'),
        additional_params=image_params.get('additionalParams')
    )
    
    # Convert to base64 for easy transfer
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return {
        "success": True,
        "image_data": img_str,
        "format": "PNG",
        "encoding": "base64"
    }
