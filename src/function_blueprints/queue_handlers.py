"""
Queue handlers for content generation pipeline
"""
import azure.functions as func
import json
import logging
from typing import Dict, Any
from src.shared.queue_client import get_queue_client
from src.tools.copywriter_tool import create_social_content
from src.tools.search_database_media_tool import search_database_media_impl
from src.tools.search_online_media_tool import search_online_media_impl

bp = func.Blueprint()

@bp.queue_trigger(arg_name="msg",
                 queue_name="content-tasks",
                 connection="AzureWebJobsStorage")
async def process_content_task(msg: func.QueueMessage,
                       context: func.Context) -> None:
    """
    Process content generation tasks from the queue.
    Each message contains a task type and relevant data.
    """
    try:
        data = json.loads(msg.get_body().decode('utf-8'))
        task_type = data.get('taskType')
        run_trace_id = data.get('runTraceId')
        
        if not all([task_type, run_trace_id]):
            raise ValueError("Missing required fields in queue message")
            
        logging.info(f"Processing {task_type} task - Trace ID: {run_trace_id}")
        
        result = None
        next_queue = None
        
        # Route to appropriate tool based on task type
        if task_type == "generate_content":
            result = await create_social_content(
                brand_document=data.get('brandDocument'),
                post_plan_document=data.get('postPlanDocument'),
                run_trace_id=run_trace_id
            )
            next_queue = "media-tasks" if result.get("status") == "completed" else "error-tasks"
            
        elif task_type == "search_media":
            # Search both database and online in parallel
            db_results = search_database_media_impl(query=data.get('query', ''))
            online_results = search_online_media_impl(query=data.get('query', ''))
            result = {
                "database_results": db_results,
                "online_results": online_results,
                "status": "completed"
            }
            next_queue = "content-tasks"  # Back to content generation with media results
            
        # Add more task types as needed
        
        if result and result.get("status") == "completed":
            # Queue next task
            next_msg = {
                "runTraceId": run_trace_id,
                "previousResult": result,
                **data  # Include original data for context
            }
            output_queue = get_queue_client(next_queue)
            output_queue.send_message(json.dumps(next_msg))
            logging.info(f"Queued next task in {next_queue} - Trace ID: {run_trace_id}")
        else:
            # Handle error
            error_queue = get_queue_client("error-tasks")
            error_queue.send_message(json.dumps({
                "runTraceId": run_trace_id,
                "error": result.get("error", "Unknown error"),
                "taskType": task_type,
                "originalMessage": data
            }))
            
    except Exception as e:
        error_msg = f"Error processing task: {str(e)}"
        logging.error(f"{error_msg} - Trace ID: {run_trace_id if 'run_trace_id' in locals() else 'unknown'}")
        error_queue = get_queue_client("error-tasks")
        error_queue.send_message(json.dumps({
            "runTraceId": run_trace_id if 'run_trace_id' in locals() else None,
            "error": error_msg,
            "taskType": task_type if 'task_type' in locals() else None,
            "originalMessage": data if 'data' in locals() else None
        }))
