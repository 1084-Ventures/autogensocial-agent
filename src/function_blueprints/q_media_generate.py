import json
import azure.functions as func

from src.specs.queue.message import QueueMessage
from src.shared.state import RunStateStore


bp = func.Blueprint()


def _stub_generate_image(run_trace_id: str) -> dict:
    media_ref = f"media/{run_trace_id}.png"
    return {
        "mediaRef": media_ref,
        "promptUsed": "stubbed",
    }


@bp.function_name(name="q_media_generate")
@bp.queue_trigger(
    arg_name="msg",
    queue_name="media-tasks",
    connection="AzureWebJobsStorage",
)
@bp.queue_output(
    arg_name="publish_queue",
    queue_name="publish-tasks",
    connection="AzureWebJobsStorage",
)
def q_media_generate(msg: func.QueueMessage, publish_queue: func.Out[str]) -> None:
    body = msg.get_body().decode("utf-8")
    data = json.loads(body)
    q = QueueMessage(**data)

    # Mark phase start
    RunStateStore.set_status(q.runTraceId, phase="image", status="in_progress")

    # Generate image (stub)
    result = _stub_generate_image(q.runTraceId)

    # Mark phase complete
    RunStateStore.set_status(
        q.runTraceId, phase="image", status="completed", summary=result
    )

    # Enqueue publish
    next_msg = QueueMessage(
        runTraceId=q.runTraceId,
        brandId=q.brandId,
        postPlanId=q.postPlanId,
        step="publish",
        agent="none",
        refs={"contentRef": q.refs.contentRef if q.refs else None, "mediaRef": result["mediaRef"]},
    )
    publish_queue.set(next_msg.model_dump_json())

