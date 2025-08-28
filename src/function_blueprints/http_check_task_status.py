import azure.functions as func
from src.specs.http.check_task_status import TaskStatusResponse
from src.specs.common.ids import RunRef
from src.shared.state import RunStateStore


bp = func.Blueprint()


@bp.function_name(name="check_task_status")
@bp.route(route="check_task_status", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def check_task_status(req: func.HttpRequest) -> func.HttpResponse:
    run_trace_id = req.params.get("runTraceId")
    if not run_trace_id:
        try:
            body = req.get_json()
            run_trace_id = body.get("runTraceId") if isinstance(body, dict) else None
        except Exception:
            run_trace_id = None

    if not run_trace_id:
        return func.HttpResponse("Missing runTraceId", status_code=400)

    state = RunStateStore.get_status(run_trace_id)
    if state is None:
        # Not found yet; treat as pending orchestrate
        resp = TaskStatusResponse(
            runTraceId=run_trace_id,
            currentPhase="orchestrate",
            status="pending",
            isComplete=False,
            lastUpdateUtc=None,
            summary=None,
        )
    else:
        resp = TaskStatusResponse(**state)

    return func.HttpResponse(
        body=resp.model_dump_json(),
        mimetype="application/json",
        status_code=200,
    )

