"""
Tool for processing publishing tasks
"""
import logging
from typing import Dict, Any
from datetime import datetime

from src.shared.cosmos_client import get_cosmos_container



def process_publish_task_impl(
    run_trace_id: str,
    brand_document: Dict[str, Any],
    post_plan_document: Dict[str, Any],
    copywriter_response: Dict[str, Any],
    generated_image_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process a publishing task with the given parameters.
    Args:
        run_trace_id (str): The trace ID for tracking
        brand_document (Dict[str, Any]): The brand document
        post_plan_document (Dict[str, Any]): The post plan document
        copywriter_response (Dict[str, Any]): The copywriter response
        generated_image_data (Dict[str, Any]): The generated image data
    Returns:
        Dict[str, Any]: The publishing result
    """
    logging.info(f"Processing publishing task - Trace ID: {run_trace_id}")
    post_document = {
        "id": run_trace_id,  # Use trace ID as post ID
        "brandId": brand_document["id"],
        "postPlanId": post_plan_document["id"],
        "content": copywriter_response.get("content"),
        "imageData": generated_image_data,
        "status": "ready_to_publish",
        "createdAt": datetime.utcnow().isoformat(),
        "type": "post"
    }
    container = get_cosmos_container("posts")
    result = container.create_item(body=post_document)
    return {
        "success": True,
        "postId": result["id"],
        "status": result["status"]
    }

process_publish_task_tool = {
    "name": "process_publish_task",
    "description": "Publish content by saving the generated content and image to storage and preparing for social media distribution",
    "parameters": {
        "run_trace_id": {"type": "string", "description": "The trace ID for tracking"},
        "brand_document": {"type": "object", "description": "The brand document containing brand details"},
        "post_plan_document": {"type": "object", "description": "The post plan document containing content plan"},
        "copywriter_response": {"type": "object", "description": "The response from the copywriter containing generated content"},
        "generated_image_data": {"type": "object", "description": "The generated image data including base64 encoded image"}
    },
    "implementation": process_publish_task_impl
}

def process_publish_task_impl(
    run_trace_id: str,
    brand_document: Dict[str, Any],
    post_plan_document: Dict[str, Any],
    copywriter_response: Dict[str, Any],
    generated_image_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process a publishing task with the given parameters.
    
    Args:
        run_trace_id (str): The trace ID for tracking
        brand_document (Dict[str, Any]): The brand document
        post_plan_document (Dict[str, Any]): The post plan document
        copywriter_response (Dict[str, Any]): The copywriter response
        generated_image_data (Dict[str, Any]): The generated image data
        
    Returns:
        Dict[str, Any]: The publishing result
    """
    logging.info(f"Processing publishing task - Trace ID: {run_trace_id}")
    
    # Create post document
    post_document = {
        "id": run_trace_id,  # Use trace ID as post ID
        "brandId": brand_document["id"],
        "postPlanId": post_plan_document["id"],
        "content": copywriter_response.get("content"),
        "imageData": generated_image_data,
        "status": "ready_to_publish",
        "createdAt": datetime.utcnow().isoformat(),
        "type": "post"
    }
    
    # Save to Cosmos DB
    container = get_cosmos_container("posts")
    result = container.create_item(body=post_document)
    
    return {
        "success": True,
        "postId": result["id"],
        "status": result["status"]
    }

# Attach the implementation to the tool
process_publish_task_tool.implementation = process_publish_task_impl
