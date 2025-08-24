"""
Tool for processing publishing tasks
"""
import logging
from typing import Dict, Any
from datetime import datetime
from src.shared.cosmos_client import get_cosmos_container

def process_publish_task_tool(
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
