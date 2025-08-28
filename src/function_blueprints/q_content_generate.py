import json
import os
from time import perf_counter
import azure.functions as func

from src.specs.queue.message import QueueMessage
from src.specs.agents.copywriter import CopywriterInput
from src.shared.state import RunStateStore
from src.shared.logging_utils import info as log_info, error as log_error
from src.agents.copywriter_agent_foundry import FoundryCopywriterAgent


bp = func.Blueprint()

CONTENT_QUEUE = os.getenv("CONTENT_TASKS_QUEUE", "content-tasks")
MEDIA_QUEUE = os.getenv("MEDIA_TASKS_QUEUE", "media-tasks")

def _generate_content_with_agent(run_trace_id: str, brand_id: str, post_plan_id: str) -> dict:
    agent = FoundryCopywriterAgent()
    out = agent.run(CopywriterInput(brandId=brand_id, postPlanId=post_plan_id, runTraceId=run_trace_id))
    return {
        "contentRef": out.contentRef,
        "caption": out.caption,
        "hashtags": out.hashtags,
    }


@bp.function_name(name="q_content_generate")
@bp.queue_trigger(
    arg_name="msg",
    queue_name="%CONTENT_TASKS_QUEUE%",
    connection="AZURE_STORAGE_CONNECTION_STRING",
)
@bp.queue_output(
    arg_name="media_queue",
    queue_name="%MEDIA_TASKS_QUEUE%",
    connection="AZURE_STORAGE_CONNECTION_STRING",
)
def q_content_generate(msg: func.QueueMessage, media_queue: func.Out[str]) -> None:
    start = perf_counter()
    body = msg.get_body().decode("utf-8")
    data = json.loads(body)
    q = QueueMessage(**data)

    log_info(q.runTraceId, "queue:dequeued", queue=CONTENT_QUEUE, messageId=getattr(msg, "id", None))

    # Mark phase start
    RunStateStore.set_status(
        q.runTraceId,
        phase="copywriter",
        status="in_progress",
        brand_id=q.brandId,
        post_plan_id=q.postPlanId,
    )
    log_info(q.runTraceId, "copywriter:start", brandId=q.brandId, postPlanId=q.postPlanId)
    try:
        RunStateStore.add_event(q.runTraceId, phase="copywriter", action="start")  # type: ignore[attr-defined]
    except Exception as exc:
        log_error(q.runTraceId, "run_state:add_event_failed", phase="copywriter", action="start", error=str(exc))

    # Generate content via Foundry agent
    try:
        result = _generate_content_with_agent(q.runTraceId, q.brandId, q.postPlanId)
    except Exception as exc:
        log_error(q.runTraceId, "copywriter:error", error=str(exc))
        try:
            RunStateStore.add_event(
                q.runTraceId,
                phase="copywriter",
                action="error",
                message=str(exc),
            )  # type: ignore[attr-defined]
        except Exception as exc2:
            log_error(q.runTraceId, "run_state:add_event_failed", phase="copywriter", action="error", error=str(exc2))
        RunStateStore.set_status(
            q.runTraceId,
            phase="copywriter",
            status="failed",
            summary={"error": str(exc)},
            brand_id=q.brandId,
            post_plan_id=q.postPlanId,
        )
        raise
    try:
        RunStateStore.add_event(
            q.runTraceId,
            phase="copywriter",
            action="agent_output",
            data={"contentRef": result.get("contentRef"), "captionLen": len(result.get("caption", "")), "hashtags": len(result.get("hashtags", []))},
        )  # type: ignore[attr-defined]
    except Exception as exc:
        log_error(q.runTraceId, "run_state:add_event_failed", phase="copywriter", action="agent_output", error=str(exc))

    # Mark phase complete with summary
    RunStateStore.set_status(
        q.runTraceId,
        phase="copywriter",
        status="completed",
        summary=result,
        brand_id=q.brandId,
        post_plan_id=q.postPlanId,
    )
    duration_ms = int((perf_counter() - start) * 1000)
    log_info(q.runTraceId, "copywriter:completed", durationMs=duration_ms)
    try:
        RunStateStore.add_event(q.runTraceId, phase="copywriter", action="completed")  # type: ignore[attr-defined]
    except Exception as exc:
        log_error(q.runTraceId, "run_state:add_event_failed", phase="copywriter", action="completed", error=str(exc))

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
    log_info(q.runTraceId, "copywriter:enqueued_image")
    try:
        RunStateStore.add_event(
            q.runTraceId,
            phase="copywriter",
            action="enqueued_next",
            data={"next": MEDIA_QUEUE, "step": "generate_image", "contentRef": result.get("contentRef")},
        )  # type: ignore[attr-defined]
    except Exception as exc:
        log_error(q.runTraceId, "run_state:add_event_failed", phase="copywriter", action="enqueued_next", error=str(exc))
