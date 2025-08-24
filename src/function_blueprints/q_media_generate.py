# Queue handler for media generation tasks

import azure.functions as func
import json
import logging
from src.tools.ops.process_image_task_tool import process_image_task_impl
from src.shared.queue_client import get_queue_client
from src.tools.data.get_post_plan_tool import get_post_plan_tool

bp = func.Blueprint()

@bp.queue_trigger(arg_name="msg", queue_name="media-tasks", connection="AzureWebJobsStorage")
async def handle_generate_media(msg: func.QueueMessage, context: func.Context):
    payload = json.loads(msg.get_body().decode("utf-8"))
    run_id = payload.get("runTraceId")

    try:
        logging.info(f"Processing media generation task - Trace ID: {run_id}")
        
        # Get post plan to derive image params
        post_plan_result = await get_post_plan_tool(payload["postPlanId"])
        if post_plan_result["status"] != "completed":
            raise ValueError(f"Failed to get post plan: {post_plan_result['error']}")
            
        post_plan = post_plan_result["result"]["document"]
        image_params = {
            **post_plan.get("imageParams", {}),
            "contentRef": payload.get("contentRef")
        }
        
        # Generate image
        result = await process_image_task_impl(
            run_trace_id=run_id,
            image_params=image_params
        )

        if result["status"] == "completed":
            # Queue publish task
            get_queue_client("publish-tasks").send_message(json.dumps({
                "runTraceId": run_id,
                "brandId": payload["brandId"],
                "postPlanId": payload["postPlanId"],
                "step": "publish",
                "contentRef": payload.get("contentRef"),
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
