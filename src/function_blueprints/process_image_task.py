"""
Queue-triggered function for image generation tasks
"""
import azure.functions as func
import logging
import json
import os
from typing import Dict, Any
from PIL import Image
from src.shared.queue_client import get_queue_client
from src.function_blueprints.compose_image_blueprint import compose_image

bp = func.Blueprint()

@bp.queue_trigger(arg_name="msg", 
                 queue_name="image-tasks",
                 connection="AzureWebJobsStorage")
@bp.function_name(name="process_image_task")
async def process_image_task(msg: func.QueueMessage,
                     context: func.Context) -> None:
    try:
        # Parse message data
        data = json.loads(msg.get_body().decode('utf-8'))
        run_trace_id = data.get('runTraceId')
        brand_document = data.get('brandDocument')
        post_plan_document = data.get('postPlanDocument')
        copywriter_response = data.get('copywriterResponse')
        
        if not all([run_trace_id, brand_document, post_plan_document, copywriter_response]):
            raise ValueError("Missing required fields in queue message")
        
        logging.info(f"Processing image generation task - Trace ID: {run_trace_id}")
        
        # Extract image requirements from copywriter response
        image_params = copywriter_response.get('imageParams', {})
        if not image_params:
            raise ValueError("No image parameters found in copywriter response")
            
        # Generate image
        img = compose_image(
            size=image_params.get('size'),
            background_color=image_params.get('backgroundColor'),
            base_image_url=image_params.get('baseImageUrl'),
            text_elements=image_params.get('textElements'),
            image_overlays=image_params.get('imageOverlays'),
            additional_params=image_params.get('additionalParams')
        )
        
        # Save image to blob storage and get URL
        # TODO: Implement blob storage upload
        image_url = "placeholder_url"
        
        # Add result to publishing queue
        output_msg = {
            "runTraceId": run_trace_id,
            "brandDocument": brand_document,
            "postPlanDocument": post_plan_document,
            "copywriterResponse": copywriter_response,
            "generatedImageUrl": image_url
        }
        
        output_queue = get_queue_client("publish-tasks")
        output_queue.send_message(json.dumps(output_msg))
        logging.info(f"Added content to publishing queue - Trace ID: {run_trace_id}")
        
    except Exception as e:
        error_msg = f"Error processing image task: {str(e)}"
        logging.error(error_msg)
        # Add to error queue for handling
        error_queue = get_queue_client("error-tasks")
        error_queue.send_message(json.dumps({
            "runTraceId": run_trace_id if 'run_trace_id' in locals() else None,
            "error": error_msg,
            "source": "image_generator",
            "originalMessage": data if 'data' in locals() else None
        }))
        raise
