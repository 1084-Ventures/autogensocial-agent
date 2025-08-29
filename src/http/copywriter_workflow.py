import logging
import os

import azure.functions as func
import azure.durable_functions as df
from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient

bp = df.Blueprint()


def _configure_logging() -> None:
    lvl = (os.getenv("AZURE_SDK_LOG_LEVEL") or "").upper()
    if lvl:
        level = getattr(logging, lvl, logging.INFO)
        logging.getLogger("azure").setLevel(level)
        logging.getLogger("azure.cosmos").setLevel(level)
    logging.getLogger("autogensocial").setLevel(logging.INFO)


_configure_logging()


@bp.route(route="durable_orchestrate", methods=["POST", "GET"])
async def durable_orchestrate(req: func.HttpRequest, starter: str) -> func.HttpResponse:
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
        "durable_orchestrator",
        None,
        {"brandId": brand_id, "postPlanId": post_plan_id},
    )
    logging.getLogger("autogensocial").info("Started orchestration %s", instance_id)
    return client.create_check_status_response(req, instance_id)


@bp.orchestration_trigger(context_name="context")
def durable_orchestrator(context: df.DurableOrchestrationContext):
    payload = context.get_input()
    content_ref = yield context.call_activity("copywriter_activity", payload)
    return {"contentRef": content_ref}


@bp.activity_trigger(input_name="payload")
def copywriter_activity(payload: dict) -> str:
    brand_id = payload.get("brandId")
    post_plan_id = payload.get("postPlanId")
    logger = logging.getLogger("autogensocial")

    endpoint = os.getenv("PROJECT_ENDPOINT")
    agent_id = os.getenv("COPYWRITER_AGENT_ID")
    content_ref: str

    if endpoint and agent_id:
        try:
            credential = DefaultAzureCredential()
            client = AgentsClient(endpoint, credential)
            instructions = (
                f"Write social media copy for brand {brand_id} and plan {post_plan_id}."
            )
            run = client.create_thread_and_run(
                agent_id=agent_id,
                instructions=instructions,
            )
            content_ref = run.id
        except Exception as exc:  # pragma: no cover - best effort
            logger.exception("Failed to invoke copywriter agent: %s", exc)
            content_ref = f"draft:{brand_id}:{post_plan_id}"
    else:
        logger.warning(
            "Agent configuration missing; returning placeholder contentRef"
        )
        content_ref = f"draft:{brand_id}:{post_plan_id}"

    logger.info(
        "Generated contentRef %s for brand %s plan %s",
        content_ref,
        brand_id,
        post_plan_id,
    )
    return content_ref
