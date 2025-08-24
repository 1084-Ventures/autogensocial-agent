import azure.functions as func
from src.specs.functions.orchestrate_content_spec import OrchestrateContentRequest, OrchestrateContentResponse, OrchestrateContentErrorResponse
from src.tools.get_brand_tool import get_brand_tool
from src.tools.get_post_plan_tool import get_post_plan_tool
from src.specs.common.trace_logger_spec import TraceLogEvent
from src.shared.queue_client import get_queue_client
import json
import os
import time
import logging
from datetime import datetime

bp = func.Blueprint()

def log_event(run_trace_id: str, event: str, level: str = "INFO", data: dict = None):
    """Log an event using TraceLogEvent model."""
    trace_event = TraceLogEvent(
        runTraceId=run_trace_id,
        event=event,
        timestamp=datetime.utcnow(),
        level=level,
        data=data
    )
    log_func = getattr(logging, level.lower(), logging.info)
    log_func(f"{trace_event.event} - Trace ID: {trace_event.runTraceId}")


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

@bp.route(route="orchestrate_content")
@bp.function_name(name="orchestrate_content")
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
