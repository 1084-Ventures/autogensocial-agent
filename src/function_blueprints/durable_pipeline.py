import uuid
import azure.functions as func
import azure.durable_functions as df

from src.specs.http.orchestrate_content import (
    OrchestrateContentRequest,
    OrchestrateContentResponse,
    ErrorResponse,
)
from src.function_blueprints.q_content_generate import _generate_content_with_agent
from src.function_blueprints.q_media_generate import _generate_image_via_agent
from src.function_blueprints.q_publish_post import _persist_publish

bp = func.Blueprint()


@bp.function_name(name="durable_http_start")
@bp.route(route="durable_orchestrate", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
@df.durable_client_input(client_name="client")
async def durable_http_start(
    req: func.HttpRequest, client: df.DurableOrchestrationClient
) -> func.HttpResponse:
    try:
        data = req.get_json()
    except ValueError:
        err = ErrorResponse(message="Invalid JSON body")
        return func.HttpResponse(
            err.model_dump_json(), mimetype="application/json", status_code=400
        )
    try:
        parsed = OrchestrateContentRequest(**data)
    except Exception as exc:  # pylint: disable=broad-except
        err = ErrorResponse(message=f"Invalid request: {exc}")
        return func.HttpResponse(
            err.model_dump_json(), mimetype="application/json", status_code=400
        )

    run_trace_id = uuid.uuid4().hex
    instance_id = await client.start_new(
        "durable_orchestrator",
        run_trace_id,
        {
            "runTraceId": run_trace_id,
            "brandId": parsed.brandId,
            "postPlanId": parsed.postPlanId,
        },
    )
    check_status = client.create_check_status_response(req, instance_id)
    resp = OrchestrateContentResponse(accepted=True, runTraceId=run_trace_id)
    return func.HttpResponse(
        body=resp.model_dump_json(),
        mimetype="application/json",
        status_code=202,
        headers=check_status.headers,
    )


@bp.function_name(name="durable_orchestrator")
@df.orchestration_trigger(context_name="context")
def durable_orchestrator(context: df.DurableOrchestrationContext):
    data = context.get_input() or {}
    content = yield context.call_activity("durable_generate_content", data)
    media_input = {**data, **content}
    media = yield context.call_activity("durable_generate_media", media_input)
    publish_input = {**data, **content, **media}
    result = yield context.call_activity("durable_publish_post", publish_input)
    return result


@bp.function_name(name="durable_generate_content")
@df.activity_trigger(input_name="data")
def durable_generate_content(data: dict) -> dict:
    return _generate_content_with_agent(
        data["runTraceId"], data["brandId"], data["postPlanId"]
    )


@bp.function_name(name="durable_generate_media")
@df.activity_trigger(input_name="data")
def durable_generate_media(data: dict) -> dict:
    return _generate_image_via_agent(
        run_trace_id=data["runTraceId"],
        brand_id=data["brandId"],
        post_plan_id=data["postPlanId"],
        content_ref=data.get("contentRef"),
    )


@bp.function_name(name="durable_publish_post")
@df.activity_trigger(input_name="data")
def durable_publish_post(data: dict) -> dict:
    return _persist_publish(
        run_trace_id=data["runTraceId"],
        brand_id=data["brandId"],
        post_plan_id=data["postPlanId"],
        content_ref=data.get("contentRef"),
        media_ref=data.get("mediaRef"),
    )
