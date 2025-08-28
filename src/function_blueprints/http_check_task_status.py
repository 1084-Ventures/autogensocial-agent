import azure.functions as func
from src.specs.http.check_task_status import TaskStatusResponse
from src.specs.common.ids import RunRef
from src.shared.state import RunStateStore
from src.shared.logging_utils import info as log_info, error as log_error


bp = func.Blueprint()


@bp.function_name(name="check_task_status")
@bp.route(route="check_task_status", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def check_task_status(req: func.HttpRequest) -> func.HttpResponse:
    run_trace_id = req.params.get("runTraceId")
    if not run_trace_id:
        try:
            body = req.get_json()
            run_trace_id = body.get("runTraceId") if isinstance(body, dict) else None
        except Exception as exc:
            log_error(None, "status:bad_json", error=str(exc))
            run_trace_id = None

    log_info(run_trace_id, "status:request")

    if not run_trace_id:
        log_error(None, "status:missing_runTraceId")
        return func.HttpResponse("Missing runTraceId", status_code=400)

    state = RunStateStore.get_status(run_trace_id)
    if state is None:
        log_info(run_trace_id, "status:not_found")
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
        log_info(run_trace_id, "status:found", phase=state.get("currentPhase"), status=state.get("status"))
        resp = TaskStatusResponse(**state)

    return func.HttpResponse(
        body=resp.model_dump_json(),
        mimetype="application/json",
        status_code=200,
    )

