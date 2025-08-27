import json
import azure.functions as func

from src.specs.queue.message import QueueMessage
from src.shared.state import RunStateStore


bp = func.Blueprint()


def _stub_generate_content(brand_id: str, post_plan_id: str, run_trace_id: str) -> dict:
    """Stubbed copywriter agent output."""
    content_ref = f"content/{run_trace_id}.json"
    return {
        "contentRef": content_ref,
        "caption": f"Sample caption for brand {brand_id} plan {post_plan_id}",
        "hashtags": ["#autogensocial", "#sample"],
    }


@bp.function_name(name="q_content_generate")
@bp.queue_trigger(
    arg_name="msg",
    queue_name="content-tasks",
    connection="AzureWebJobsStorage",
)
@bp.queue_output(
    arg_name="media_queue",
    queue_name="media-tasks",
    connection="AzureWebJobsStorage",
)
def q_content_generate(msg: func.QueueMessage, media_queue: func.Out[str]) -> None:
    body = msg.get_body().decode("utf-8")
    data = json.loads(body)
    q = QueueMessage(**data)

    # Mark phase start
    RunStateStore.set_status(q.runTraceId, phase="copywriter", status="in_progress")

    # Generate content (stub)
    result = _stub_generate_content(q.brandId, q.postPlanId, q.runTraceId)

    # Mark phase complete with summary
    RunStateStore.set_status(
        q.runTraceId, phase="copywriter", status="completed", summary=result
    )

    # Enqueue image generation
    next_msg = QueueMessage(
        runTraceId=q.runTraceId,
        brandId=q.brandId,
        postPlanId=q.postPlanId,
        step="generate_image",
        agent="composer-image",
        refs={"contentRef": result["contentRef"]},
    )
    media_queue.set(next_msg.model_dump_json())

