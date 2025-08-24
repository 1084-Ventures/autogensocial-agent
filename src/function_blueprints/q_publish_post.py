# Queue handler for post publishing tasks

import azure.functions as func
import json
import logging
from src.tools.ops.process_publish_task_tool import process_publish_task_impl
from src.shared.queue_client import get_queue_client

bp = func.Blueprint()

@bp.queue_trigger(arg_name="msg", queue_name="publish-tasks", connection="AzureWebJobsStorage")
async def handle_publish_post(msg: func.QueueMessage, context: func.Context):
    payload = json.loads(msg.get_body().decode("utf-8"))
    run_id = payload.get("runTraceId")

    try:
        logging.info(f"Processing publish task - Trace ID: {run_id}")
        
        result = await process_publish_task_impl(
            run_trace_id=run_id,
            brand_id=payload["brandId"],
            post_plan_id=payload["postPlanId"],
            media_ref=payload.get("mediaRef")
        )

        if result["status"] != "completed":
            # Queue error task
            get_queue_client("error-tasks").send_message(json.dumps({
                "runTraceId": run_id,
                "error": result["error"]
            }))

    except Exception as e:
        logging.exception(f"Queue handler failed - Trace ID: {run_id}")
        get_queue_client("error-tasks").send_message(json.dumps({
            "runTraceId": run_id,
            "error": {"message": str(e)}
        }))
