"""
Queue-triggered function for content publishing tasks
"""
import azure.functions as func
import logging
import json
import os
from typing import Dict, Any
from src.shared.queue_client import get_queue_client
from src.shared.cosmos_client import get_cosmos_container

bp = func.Blueprint()

@bp.queue_trigger(arg_name="msg", 
                 queue_name="publish-tasks",
                 connection="AzureWebJobsStorage")
@bp.function_name(name="process_publish_task")
async def process_publish_task(msg: func.QueueMessage,
                       context: func.Context) -> None:
    try:
        # Parse message data
        data = json.loads(msg.get_body().decode('utf-8'))
        run_trace_id = data.get('runTraceId')
        brand_document = data.get('brandDocument')
        post_plan_document = data.get('postPlanDocument')
        copywriter_response = data.get('copywriterResponse')
        generated_image_url = data.get('generatedImageUrl')
        
        if not all([run_trace_id, brand_document, post_plan_document, 
                   copywriter_response, generated_image_url]):
            raise ValueError("Missing required fields in queue message")
        
        logging.info(f"Processing publishing task - Trace ID: {run_trace_id}")
        
        # Create the final post document
        post_document = {
            "id": run_trace_id,  # Use trace ID as post ID
            "brandId": brand_document["id"],
            "postPlanId": post_plan_document["id"],
            "content": copywriter_response.get("content"),
            "imageUrl": generated_image_url,
            "status": "ready_to_publish",
            "createdAt": context.datetime.isoformat(),
            "type": "post"
        }
        
        # Save to Cosmos DB
        container = get_cosmos_container("posts")
        container.create_item(body=post_document)
        logging.info(f"Saved post document - ID: {post_document['id']}")
        
        # TODO: Implement actual social media publishing
        # This would integrate with various social media APIs
        
    except Exception as e:
        error_msg = f"Error processing publishing task: {str(e)}"
        logging.error(error_msg)
        # Add to error queue for handling
        error_queue = get_queue_client("error-tasks")
        error_queue.send_message(json.dumps({
            "runTraceId": run_trace_id if 'run_trace_id' in locals() else None,
            "error": error_msg,
            "source": "publisher",
            "originalMessage": data if 'data' in locals() else None
        }))
        raise
