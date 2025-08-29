import uuid
import azure.functions as func
import azure.durable_functions as df

from src.specs.http.orchestrate_content import (
    OrchestrateContentRequest,
    OrchestrateContentResponse,
    ErrorResponse,
)
from src.function_blueprints.agent_tasks import (
    generate_content_with_foundry_agent,
    generate_image_with_foundry_agent,
    persist_publish,
    load_post_plan,
    post_to_channel,
)
from src.specs.agents.publish import PublishInput

# Use Durable Functions Blueprint, compatible with FunctionApp.register_functions
bp = df.Blueprint()


@bp.function_name(name="durable_http_start")
@bp.route(route="durable_orchestrate", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
@bp.durable_client_input(client_name="client")
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
@bp.orchestration_trigger(context_name="context")
def durable_orchestrator(context: df.DurableOrchestrationContext):
    data = context.get_input() or {}
    plan = yield context.call_activity("durable_load_post_plan", data)
    content = yield context.call_activity("durable_generate_content", data)

    media = {}
    media_plan = (plan or {}).get("media") or {}
    requires_media = media_plan.get("type") not in (None, "text-only")
    if requires_media:
        media_input = {**data, **content}
        media = yield context.call_activity("durable_generate_media", media_input)

    publish_input = {**data, **content, **media}

    channels = (plan or {}).get("channels") or []
    if channels:
        tasks = []
        for ch in channels:
            ch_input = {**publish_input, "channel": ch}
            tasks.append(context.call_activity("durable_post_to_channel", ch_input))
        if tasks:
            yield context.task_all(tasks)

    result = yield context.call_activity("durable_persist_post", publish_input)
    return result


@bp.function_name(name="durable_generate_content")
@bp.activity_trigger(input_name="data")
def durable_generate_content(data: dict) -> dict:
    return generate_content_with_foundry_agent(
        data["runTraceId"], data["brandId"], data["postPlanId"]
    )


@bp.function_name(name="durable_generate_media")
@bp.activity_trigger(input_name="data")
def durable_generate_media(data: dict) -> dict:
    return generate_image_with_foundry_agent(
        run_trace_id=data["runTraceId"],
        brand_id=data["brandId"],
        post_plan_id=data["postPlanId"],
        content_ref=data.get("contentRef"),
    )


@bp.function_name(name="durable_load_post_plan")
@bp.activity_trigger(input_name="data")
def durable_load_post_plan(data: dict) -> dict:
    return load_post_plan(brand_id=data["brandId"], post_plan_id=data["postPlanId"])


@bp.function_name(name="durable_post_to_channel")
@bp.activity_trigger(input_name="data")
def durable_post_to_channel(data: dict) -> dict:
    publish = PublishInput(
        runTraceId=data["runTraceId"],
        brandId=data["brandId"],
        postPlanId=data["postPlanId"],
        contentRef=data.get("contentRef"),
        mediaRef=data.get("mediaRef"),
    )
    return post_to_channel(data["channel"], publish)


@bp.function_name(name="durable_persist_post")
@bp.activity_trigger(input_name="data")
def durable_persist_post(data: dict) -> dict:
    result = persist_publish(
        PublishInput(
            runTraceId=data["runTraceId"],
            brandId=data["brandId"],
            postPlanId=data["postPlanId"],
            contentRef=data.get("contentRef"),
            mediaRef=data.get("mediaRef"),
        )
    )
    return result.model_dump()
