import azure.functions as func
import json
import logging
import os
import time
from datetime import datetime
from src.specs.functions.orchestrate_content_spec import (
    OrchestrateContentRequest,
    OrchestrateContentResponse,
    OrchestrateContentErrorResponse
)
from src.tools.data.get_brand_tool import get_brand_tool
from src.tools.data.get_post_plan_tool import get_post_plan_tool
from src.specs.common.trace_logger_spec import TraceLogEvent
from src.shared.queue_client import get_queue_client
from src.shared.trace_logger import AzureTraceLogger

bp = func.Blueprint()

def error_response(message: str, status_code: int = 400, error_code: str = "BAD_REQUEST") -> func.HttpResponse:
    """Create a standardized error response"""
    return func.HttpResponse(
        json.dumps({
            "success": False,
            "message": message,
            "errorCode": error_code
        }),
        status_code=status_code,
        mimetype="application/json"
    )

async def log_event(run_trace_id: str, event: str, level: str = "INFO", details: dict = None):
    """Log an event using TraceLogEvent and AzureTraceLogger"""
    logger = AzureTraceLogger(run_trace_id)
    await logger.log_event(
        phase=event,
        status=level,
        details=details
    )
    
    # Also log to Application Insights
    log_func = logging.info if level == "INFO" else logging.error
    log_func(f"{event} - Trace ID: {run_trace_id}")
    if details:
        log_func(f"Details: {json.dumps(details)}")

@bp.function_name("orchestrate_content")
@bp.route(route="orchestrate_content", auth_level=func.AuthLevel.FUNCTION)
async def orchestrate_content(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP trigger to start the content orchestration process.
    Validates input, checks documents, and enqueues the first content generation task.
    """
    try:
        # Parse request
        request = OrchestrateContentRequest(**req.get_json())
        run_trace_id = f"run-{int(time.time())}"
        
        # Log received
        await log_event(run_trace_id, "REQUEST_RECEIVED", details={
            "brandId": request.brandId,
            "postPlanId": request.payload.get("postPlanId")
        })
        
        # Validate brand document
        brand_result = await get_brand_tool(request.brandId)
        if brand_result["status"] != "completed":
            await log_event(run_trace_id, "BRAND_NOT_FOUND", "ERROR", brand_result["error"])
            return error_response(
                f"Brand not found: {request.brandId}",
                status_code=404,
                error_code="BRAND_NOT_FOUND"
            )
            
        # Validate post plan document
        post_plan_result = await get_post_plan_tool(request.payload["postPlanId"])
        if post_plan_result["status"] != "completed":
            await log_event(run_trace_id, "POST_PLAN_NOT_FOUND", "ERROR", post_plan_result["error"])
            return error_response(
                f"Post plan not found: {request.payload['postPlanId']}",
                status_code=404,
                error_code="POST_PLAN_NOT_FOUND"
            )
            
        # Queue content generation task
        content_queue = get_queue_client("content-tasks")
        queue_msg = {
            "runTraceId": run_trace_id,
            "brandId": request.brandId,
            "postPlanId": request.payload["postPlanId"],
            "step": "generate_content"
        }
        content_queue.send_message(json.dumps(queue_msg))
        
        await log_event(run_trace_id, "TASK_QUEUED", details=queue_msg)
        
        # Return success response
        return func.HttpResponse(
            json.dumps({
                "success": True,
                "runTraceId": run_trace_id,
                "message": "Content generation task queued successfully"
            }),
            status_code=202,
            mimetype="application/json"
        )
            
    except ValueError as e:
        return error_response(str(e), error_code="VALIDATION_ERROR")
    except Exception as e:
        logging.exception("Orchestration failed")
        return error_response(str(e), status_code=500, error_code="INTERNAL_ERROR")

def update_post_status(post_id, status):
    # Stub for Cosmos DB update
    logging.info(f"Update post {post_id} status to {status}")


# Call the Copywriter Agent as an Azure AI Foundry agent
async def call_copywriter_agent(brand_document, post_plan_document, run_trace_id):
    project_endpoint = os.environ.get("PROJECT_ENDPOINT")
    model_name = os.environ.get("MODEL_DEPLOYMENT_NAME")
    if not project_endpoint or not model_name:
        raise EnvironmentError("PROJECT_ENDPOINT and MODEL_DEPLOYMENT_NAME environment variables must be set.")

    logging.debug(f"Using project endpoint: {project_endpoint}")
    logging.debug(f"Using model name: {model_name}")
    
    try:
        from src.function_blueprints.agent_factory import create_copywriter_agent
        from src.specs.agents.copywriter_agent_spec import CopywriterAgentRequest
        
        logging.debug("Creating copywriter agent...")
        agent = create_copywriter_agent(
            project_endpoint=project_endpoint,
            model_name=model_name
        )
        
        # Create the request object
        request = CopywriterAgentRequest(
            brand_document=brand_document,
            post_plan_document=post_plan_document,
            run_trace_id=run_trace_id
        )
        
        # Process the content request
        response = await agent.create_content(request)
        logging.debug(f"Generated content with trace ID: {response.traceId}")
        
        return response
        
    except Exception as e:
        error_msg = f"Error with AI Project client: {str(e)}"
        logging.error(error_msg)
        raise RuntimeError(error_msg)

@bp.route(route="orchestrate_content_handler")
@bp.function_name(name="orchestrate_content_handler")
async def orchestrate_content_handler(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Processing orchestrate content request')
    
    if not req.get_body():
        error_response = OrchestrateContentErrorResponse(
            message="Request body is required",
            error_code="MISSING_BODY"
        )
        return func.HttpResponse(
            error_response.model_dump_json(),
            status_code=400,
            mimetype="application/json"
        )

    try:
        req_body = req.get_json()
    except ValueError:
        error_response = OrchestrateContentErrorResponse(
            message="Invalid JSON in request body",
            error_code="INVALID_JSON"
        )
        return func.HttpResponse(
            error_response.model_dump_json(),
            status_code=400,
            mimetype="application/json"
        )

    # Validate required fields
    if 'runTraceId' not in req_body:
        error_response = OrchestrateContentErrorResponse(
            message="runTraceId is required",
            error_code="MISSING_FIELD"
        )
        return func.HttpResponse(
            error_response.model_dump_json(),
            status_code=400,
            mimetype="application/json"
        )

    if 'brandId' not in req_body:
        error_response = OrchestrateContentErrorResponse(
            message="brandId is required",
            error_code="MISSING_FIELD"
        )
        return func.HttpResponse(
            error_response.model_dump_json(),
            status_code=400,
            mimetype="application/json"
        )

    try:
        request = OrchestrateContentRequest(**req_body)
    except Exception as e:
        error_response = OrchestrateContentErrorResponse(
            message=f"Invalid request format: {str(e)}",
            error_code="INVALID_FORMAT",
            details=str(e)
        )
        return func.HttpResponse(
            error_response.model_dump_json(),
            status_code=400,
            mimetype="application/json"
        )

    run_trace_id = request.runTraceId
    log_event(run_trace_id, "Received OrchestrateContentRequest")

    # Step 1: Get Brand Document
    try:
        brand_document = get_brand_tool(request.brandId)
        log_event(run_trace_id, "Fetched brandDocument")
    except Exception as e:
        return func.HttpResponse(
            OrchestrateContentErrorResponse(message=f"Failed to fetch brand: {str(e)}").model_dump_json(),
            status_code=404,
            mimetype="application/json"
        )

    # Step 2: Get Post Plan Document
    post_plan_id = request.payload.get("postPlanId") if request.payload else None
    if not post_plan_id:
        return func.HttpResponse(
            OrchestrateContentErrorResponse(message="Missing postPlanId in payload").model_dump_json(),
            status_code=400,
            mimetype="application/json"
        )
    try:
        post_plan_document = get_post_plan_tool(post_plan_id)
        log_event(run_trace_id, "Fetched postPlanDocument")
    except Exception as e:
        return func.HttpResponse(
            OrchestrateContentErrorResponse(message=f"Failed to fetch post plan: {str(e)}").model_dump_json(),
            status_code=404,
            mimetype="application/json"
        )

    # Step 3: Update post status (stub)
    update_post_status(post_plan_id, "retrieved brand & plan")
    log_event(run_trace_id, "Updated post: retrieved brand & plan")

    # Step 4: Queue Content Generation Task
    try:
        queue_msg = {
            "taskType": "generate_content",
            "runTraceId": run_trace_id,
            "brandDocument": brand_document,
            "postPlanDocument": post_plan_document
        }
        content_queue = get_queue_client("content-tasks")
        content_queue.send_message(json.dumps(queue_msg))
        log_event(run_trace_id, "Added task to content generation queue")
    except Exception as e:
        error_msg = f"Failed to queue content generation task: {str(e)}"
        log_event(run_trace_id, error_msg, level="ERROR")
        return func.HttpResponse(
            OrchestrateContentErrorResponse(message=error_msg).model_dump_json(),
            status_code=500,
            mimetype="application/json"
        )

    # Step 5: Update post status
    update_post_status(post_plan_id, "queued_for_processing")
    log_event(run_trace_id, "Updated post: queued for processing")

    # Step 6: Return OrchestrateContentResponse with task ID
    response = OrchestrateContentResponse(
        success=True,
        message="Content generation pipeline started",
        postId=post_plan_id,
        data={
            "runTraceId": run_trace_id,
            "status": "processing_started"
        }
    )
    return func.HttpResponse(
        response.model_dump_json(),
        status_code=202,  # Accepted
        mimetype="application/json"
    )
