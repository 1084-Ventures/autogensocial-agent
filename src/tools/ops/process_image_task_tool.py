"""
Tool for processing image generation tasks with standardized response envelope
"""
import logging
from typing import Dict, Any
from src.tools.image_generator_tool import generate_social_image

def process_image_task_impl(run_trace_id: str, image_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process an image generation task with the given parameters.
    
    Args:
        run_trace_id (str): The trace ID for tracking
        image_params (Dict[str, Any]): The image generation parameters
        
    Returns:
        Dict[str, Any]: Response envelope with status, result, error, and metadata
    """
    logging.info(f"Processing image generation task - Trace ID: {run_trace_id}")
    
    try:
        if not image_params:
            raise ValueError("Image parameters are required")
        
        # Generate image using the underlying tool
        img_b64, metadata = generate_social_image(
            size=image_params.get('size'),
            background_color=image_params.get('backgroundColor'),
            base_image_url=image_params.get('baseImageUrl'),
            text_elements=image_params.get('textElements'),
            image_overlays=image_params.get('imageOverlays'),
            additional_params=image_params.get('additionalParams')
        )
        
        return {
            "status": "completed",
            "result": {
                "mediaRef": metadata["blobUrl"],
                "base64": img_b64
            },
            "error": None,
            "meta": {
                **metadata,
                "format": "PNG",
                "durationMs": metadata.get("durationMs", 0)
            }
        }
        
    except Exception as e:
        logging.exception(f"Image generation failed - Trace ID: {run_trace_id}")
        return {
            "status": "failed",
            "result": None,
            "error": {
                "code": "IMAGE_GEN_ERROR",
                "message": str(e)
            },
            "meta": {
                "durationMs": 0
            }
        }
