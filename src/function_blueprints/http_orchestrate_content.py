import json
import os
import uuid
from datetime import datetime, timezone
from time import perf_counter
import azure.functions as func

from src.specs.http.orchestrate_content import (
    OrchestrateContentRequest,
    OrchestrateContentResponse,
    ErrorResponse,
)
from src.specs.queue.message import QueueMessage
from src.shared.state import RunStateStore
from src.shared.logging_utils import info as log_info, error as log_error


bp = func.Blueprint()

CONTENT_QUEUE = os.getenv("CONTENT_TASKS_QUEUE", "content-tasks")

@bp.function_name(name="orchestrate_content")
@bp.route(route="orchestrate_content", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
@bp.queue_output(
    arg_name="content_queue",
    queue_name="%CONTENT_TASKS_QUEUE%",
    connection="AZURE_STORAGE_CONNECTION_STRING",
)
def orchestrate_content(req: func.HttpRequest, content_queue: func.Out[str]) -> func.HttpResponse:
    start = perf_counter()
    try:
        data = req.get_json()
    except ValueError:
        log_error(None, "orchestrate:invalid_json")
        err = ErrorResponse(message="Invalid JSON body")
        return func.HttpResponse(
            body=err.model_dump_json(),
            mimetype="application/json",
            status_code=400,
        )

    try:
        parsed = OrchestrateContentRequest(**data)
    except Exception as ex:
        log_error(None, "orchestrate:invalid_request", error=str(ex))
        err = ErrorResponse(message=f"Invalid request: {str(ex)}")
        return func.HttpResponse(
            body=err.model_dump_json(),
            mimetype="application/json",
            status_code=400,
        )

    run_trace_id = uuid.uuid4().hex

    # Seed the state store
    RunStateStore.set_status(
        run_trace_id,
        phase="orchestrate",
        status="in_progress",
        summary={"brandId": parsed.brandId, "postPlanId": parsed.postPlanId},
        brand_id=parsed.brandId,
        post_plan_id=parsed.postPlanId,
    )
    log_info(run_trace_id, "orchestrate:accepted", brandId=parsed.brandId, postPlanId=parsed.postPlanId)
    try:
        RunStateStore.add_event(
            run_trace_id,
            phase="orchestrate",
            action="accepted",
            data={"brandId": parsed.brandId, "postPlanId": parsed.postPlanId},
        )  # type: ignore[attr-defined]
    except Exception as exc:
        log_error(run_trace_id, "run_state:add_event_failed", phase="orchestrate", action="accepted", error=str(exc))

    # Enqueue first step: generate_content
    qmsg = QueueMessage(
        runTraceId=run_trace_id,
        brandId=parsed.brandId,
        postPlanId=parsed.postPlanId,
        step="generate_content",
        agent="copywriter",
    )
    content_queue.set(qmsg.model_dump_json())
    duration_ms = int((perf_counter() - start) * 1000)
    log_info(run_trace_id, "orchestrate:enqueued_content", durationMs=duration_ms)
    try:
        RunStateStore.add_event(
            run_trace_id,
            phase="orchestrate",
            action="enqueued_next",
            data={"next": CONTENT_QUEUE, "step": "generate_content"},
        )  # type: ignore[attr-defined]
    except Exception as exc:
        log_error(run_trace_id, "run_state:add_event_failed", phase="orchestrate", action="enqueued_next", error=str(exc))

    resp = OrchestrateContentResponse(accepted=True, runTraceId=run_trace_id)
    return func.HttpResponse(
        body=resp.model_dump_json(),
        mimetype="application/json",
        status_code=202,
    )
