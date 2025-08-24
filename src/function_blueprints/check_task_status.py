# Function for checking task status

import azure.functions as func
import logging
import json
from src.shared.cosmos_client import get_cosmos_container
from src.shared.trace_logger import AzureTraceLogger

bp = func.Blueprint()

@bp.route(route="check_task_status", auth_level=func.AuthLevel.FUNCTION)
@bp.function_name(name="check_task_status")
async def check_task_status(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP trigger to check the status of a content generation task.
    Returns the current status and any error information.
    """
    # Get trace ID from query parameters
    trace_id = req.params.get('traceId')
    if not trace_id:
        return func.HttpResponse(
            json.dumps({
                "success": False,
                "message": "traceId parameter is required",
                "errorCode": "MISSING_PARAMETER"
            }),
            status_code=400,
            mimetype="application/json"
        )
        
    try:
        # Use AzureTraceLogger to get status
        logger = AzureTraceLogger(trace_id)
        status = await logger.get_run_status()
        
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "runTraceId": trace_id,
                "status": status
            }),
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.exception(f"Failed to check status - Trace ID: {trace_id}")
        return func.HttpResponse(
            json.dumps({
                "success": False,
                "message": str(e),
                "errorCode": "STATUS_CHECK_ERROR"
            }),
            status_code=500,
            mimetype="application/json"
        )
    
    try:
        # Query agent runs container for task status
        container = get_cosmos_container("agentRuns")
        query = f"SELECT * FROM c WHERE c.runTraceId = '{trace_id}' ORDER BY c._ts DESC"
        items = list(container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        
        if not items:
            return func.HttpResponse(
                f"No task found with trace ID: {trace_id}",
                status_code=404
            )
            
        # Get latest status
        latest_status = items[0]
        
        # Also check posts container for final status
        posts_container = get_cosmos_container("posts")
        posts_query = f"SELECT * FROM c WHERE c.id = '{trace_id}'"
        post_items = list(posts_container.query_items(
            query=posts_query,
            enable_cross_partition_query=True
        ))
        
        response = {
            "traceId": trace_id,
            "currentPhase": latest_status.get("phase", "unknown"),
            "status": latest_status.get("status", "unknown"),
            "startedAt": latest_status.get("startedAt"),
            "lastUpdatedAt": latest_status.get("lastUpdatedAt"),
            "error": latest_status.get("error"),
            "isComplete": len(post_items) > 0,  # True if post exists
            "postId": post_items[0]["id"] if post_items else None
        }
        
        return func.HttpResponse(
            json.dumps(response),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        error_msg = f"Error checking task status: {str(e)}"
        logging.error(error_msg)
        return func.HttpResponse(
            error_msg,
            status_code=500
        )
