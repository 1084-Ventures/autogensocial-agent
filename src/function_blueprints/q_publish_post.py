import json
from datetime import datetime, timezone
import azure.functions as func

from src.specs.queue.message import QueueMessage
from src.shared.state import RunStateStore


bp = func.Blueprint()


def _stub_publish(run_trace_id: str, brand_id: str, post_plan_id: str, content_ref: str, media_ref: str) -> dict:
    post_id = f"post-{run_trace_id[:8]}"
    return {
        "postId": post_id,
        "publishedAtUtc": datetime.now(timezone.utc).isoformat(),
        "contentRef": content_ref,
        "mediaRef": media_ref,
    }


@bp.function_name(name="q_publish_post")
@bp.queue_trigger(
    arg_name="msg",
    queue_name="publish-tasks",
    connection="AzureWebJobsStorage",
)
def q_publish_post(msg: func.QueueMessage) -> None:
    body = msg.get_body().decode("utf-8")
    data = json.loads(body)
    q = QueueMessage(**data)

    # Mark phase start
    RunStateStore.set_status(q.runTraceId, phase="publish", status="in_progress")

    # Publish (stub)
    content_ref = (q.refs or {}).get("contentRef") if isinstance(q.refs, dict) else getattr(q.refs, "contentRef", None)
    media_ref = (q.refs or {}).get("mediaRef") if isinstance(q.refs, dict) else getattr(q.refs, "mediaRef", None)
    result = _stub_publish(q.runTraceId, q.brandId, q.postPlanId, content_ref, media_ref)

    # Mark complete
    RunStateStore.set_status(
        q.runTraceId, phase="publish", status="completed", summary=result
    )

