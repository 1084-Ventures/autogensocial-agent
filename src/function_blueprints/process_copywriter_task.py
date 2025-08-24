"""
Queue-triggered function for copywriting tasks
"""
import azure.functions as func
import logging
import json
import os
from typing import Dict, Any
from src.shared.queue_client import get_queue_client
from src.function_blueprints.agent_factory import create_copywriter_agent
from src.specs.agents.copywriter_agent_spec import CopywriterAgentRequest

bp = func.Blueprint()

@bp.queue_trigger(arg_name="msg", 
                 queue_name="copywriter-tasks",
                 connection="AzureWebJobsStorage")
@bp.function_name(name="process_copywriter_task")
async def process_copywriter_task(msg: func.QueueMessage,
                          context: func.Context) -> None:
    try:
        # Parse message data
        data = json.loads(msg.get_body().decode('utf-8'))
        run_trace_id = data.get('runTraceId')
        brand_document = data.get('brandDocument')
        post_plan_document = data.get('postPlanDocument')
        
        if not all([run_trace_id, brand_document, post_plan_document]):
            raise ValueError("Missing required fields in queue message")
        
        logging.info(f"Processing copywriter task - Trace ID: {run_trace_id}")
        
        # Call the copywriter agent
        project_endpoint = os.environ.get("PROJECT_ENDPOINT")
        model_name = os.environ.get("MODEL_DEPLOYMENT_NAME")
        if not project_endpoint or not model_name:
            raise EnvironmentError("PROJECT_ENDPOINT and MODEL_DEPLOYMENT_NAME environment variables must be set.")

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
        logging.info(f"Generated content with trace ID: {response.traceId}")
        
        # Add result to image generation queue
        output_msg = {
            "runTraceId": run_trace_id,
            "brandDocument": brand_document,
            "postPlanDocument": post_plan_document,
            "copywriterResponse": response.dict()
        }
        
        output_queue = get_queue_client("image-tasks")
        output_queue.send_message(json.dumps(output_msg))
        logging.info(f"Added content to image generation queue - Trace ID: {run_trace_id}")
        
    except Exception as e:
        error_msg = f"Error processing copywriter task: {str(e)}"
        logging.error(error_msg)
        # Add to error queue for handling
        error_queue = get_queue_client("error-tasks")
        error_queue.send_message(json.dumps({
            "runTraceId": run_trace_id if 'run_trace_id' in locals() else None,
            "error": error_msg,
            "source": "copywriter",
            "originalMessage": data if 'data' in locals() else None
        }))
        raise
