import logging
import os

import azure.functions as func
import azure.durable_functions as df
from src.agents.copywriter_agent import generate_content_ref
from src.specs.models import (
    OrchestrateRequest,
    CopywriterActivityPayload,
    ContentRefResult,
)

bp = df.Blueprint()


def _configure_logging() -> None:
    lvl = (os.getenv("AZURE_SDK_LOG_LEVEL") or "").upper()
    if lvl:
        level = getattr(logging, lvl, logging.INFO)
        logging.getLogger("azure").setLevel(level)
        logging.getLogger("azure.cosmos").setLevel(level)
    logging.getLogger("autogensocial").setLevel(logging.INFO)


_configure_logging()


@bp.route(route="autogensocial/orchestrate", methods=["POST", "GET"])
async def start_autogensocial(req: func.HttpRequest, starter: str) -> func.HttpResponse:
    client = df.DurableOrchestrationClient(starter)
    # Merge query and JSON body; query takes precedence if present
    try:
        body = req.get_json()
    except ValueError:
        body = {}
    payload = {
        "brandId": req.params.get("brandId") or body.get("brandId"),
        "postPlanId": req.params.get("postPlanId") or body.get("postPlanId"),
    }
    try:
        req_model = OrchestrateRequest(**payload)
    except Exception:
        return func.HttpResponse("brandId and postPlanId are required", status_code=400)

    instance_id = await client.start_new(
        "autogensocial_orchestrator",
        None,
        req_model.model_dump(),
    )
    logging.getLogger("autogensocial").info("Started orchestration %s", instance_id)
    return client.create_check_status_response(req, instance_id)


@bp.orchestration_trigger(context_name="context")
def autogensocial_orchestrator(context: df.DurableOrchestrationContext):
    # Validate and normalize the input for downstream activities
    req_model = CopywriterActivityPayload.model_validate(context.get_input())
    # Use the durable instance id as a default runTraceId for correlation
    if not req_model.runTraceId:
        req_model.runTraceId = context.instance_id
    # Update custom status for observability (safe, deterministic)
    context.set_custom_status(
        {
            "phase": "generating_content",
            "runTraceId": req_model.runTraceId,
        }
    )
    content_ref = yield context.call_activity(
        "copywriter_activity", req_model.model_dump()
    )
    context.set_custom_status(
        {
            "phase": "completed",
            "runTraceId": req_model.runTraceId,
            "contentRef": content_ref,
        }
    )
    return ContentRefResult(contentRef=content_ref).model_dump()


@bp.activity_trigger(input_name="payload")
def copywriter_activity(payload: dict) -> str:
    req = CopywriterActivityPayload.model_validate(payload)
    brand_id = req.brandId
    post_plan_id = req.postPlanId
    logger = logging.getLogger("autogensocial")
    content_ref = generate_content_ref(
        brand_id=brand_id,
        post_plan_id=post_plan_id,
        logger=logger,
    )
    logger.info(
        "Generated contentRef %s for brand %s plan %s trace %s",
        content_ref,
        brand_id,
        post_plan_id,
        req.runTraceId,
    )
    return content_ref
