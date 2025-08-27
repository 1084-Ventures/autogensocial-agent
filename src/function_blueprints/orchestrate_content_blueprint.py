import json
import uuid
from datetime import datetime, timezone
import azure.functions as func

from src.specs.http.orchestrate_content import (
    OrchestrateContentRequest,
    OrchestrateContentResponse,
    ErrorResponse,
)
from src.specs.queue.message import QueueMessage
from src.shared.state import RunStateStore


bp = func.Blueprint()


@bp.function_name(name="orchestrate_content")
@bp.route(route="orchestrate_content", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
@bp.queue_output(
    arg_name="content_queue",
    queue_name="content-tasks",
    connection="AzureWebJobsStorage",
)
def orchestrate_content(req: func.HttpRequest, content_queue: func.Out[str]) -> func.HttpResponse:
    try:
        data = req.get_json()
    except ValueError:
        err = ErrorResponse(message="Invalid JSON body")
        return func.HttpResponse(
            body=err.model_dump_json(),
            mimetype="application/json",
            status_code=400,
        )

    try:
        parsed = OrchestrateContentRequest(**data)
    except Exception as ex:
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
    )

    # Enqueue first step: generate_content
    qmsg = QueueMessage(
        runTraceId=run_trace_id,
        brandId=parsed.brandId,
        postPlanId=parsed.postPlanId,
        step="generate_content",
        agent="copywriter",
    )
    content_queue.set(qmsg.model_dump_json())

    resp = OrchestrateContentResponse(accepted=True, runTraceId=run_trace_id)
    return func.HttpResponse(
        body=resp.model_dump_json(),
        mimetype="application/json",
        status_code=202,
    )

