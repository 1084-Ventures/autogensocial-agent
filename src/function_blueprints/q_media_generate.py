"""
Queue handler for media generation tasks
"""
import azure.functions as func
import json
import logging
from src.tools.ops.process_image_task_tool import process_image_task_impl
from src.shared.queue_client import get_queue_client

bp = func.Blueprint()

@bp.queue_trigger(arg_name="msg", queue_name="media-tasks", connection="AzureWebJobsStorage")
def handle_generate_media(msg: func.QueueMessage, context: func.Context):
    payload = json.loads(msg.get_body().decode("utf-8"))
    run_id = payload.get("runTraceId")

    try:
        logging.info(f"Processing media generation task - Trace ID: {run_id}")
        
        result = process_image_task_impl(
            run_trace_id=run_id,
            image_params=payload["imageParams"]
        )

        if result["status"] == "completed":
            # Queue publish task
            get_queue_client("publish-tasks").send_message(json.dumps({
                "runTraceId": run_id,
                "brandId": payload["brandId"],
                "postPlanId": payload["postPlanId"],
                "step": "publish",
                "mediaRef": result["result"]["mediaRef"]
            }))
        else:
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
