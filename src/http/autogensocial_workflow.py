import logging
import os

import azure.functions as func
import azure.durable_functions as df
from src.agents.copywriter_agent import generate_content_ref

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
    brand_id = req.params.get("brandId")
    post_plan_id = req.params.get("postPlanId")
    if not brand_id or not post_plan_id:
        try:
            body = req.get_json()
        except ValueError:
            body = {}
        brand_id = brand_id or body.get("brandId")
        post_plan_id = post_plan_id or body.get("postPlanId")
    if not brand_id or not post_plan_id:
        return func.HttpResponse("brandId and postPlanId are required", status_code=400)

    instance_id = await client.start_new(
        "autogensocial_orchestrator",
        None,
        {"brandId": brand_id, "postPlanId": post_plan_id},
    )
    logging.getLogger("autogensocial").info("Started orchestration %s", instance_id)
    return client.create_check_status_response(req, instance_id)


@bp.orchestration_trigger(context_name="context")
def autogensocial_orchestrator(context: df.DurableOrchestrationContext):
    payload = context.get_input()
    content_ref = yield context.call_activity("copywriter_activity", payload)
    return {"contentRef": content_ref}


@bp.activity_trigger(input_name="payload")
def copywriter_activity(payload: dict) -> str:
    brand_id = payload.get("brandId")
    post_plan_id = payload.get("postPlanId")
    logger = logging.getLogger("autogensocial")
    content_ref = generate_content_ref(
        brand_id=brand_id,
        post_plan_id=post_plan_id,
        logger=logger,
    )
    logger.info(
        "Generated contentRef %s for brand %s plan %s",
        content_ref,
        brand_id,
        post_plan_id,
    )
    return content_ref
