import json
import os
from typing import Any, Optional
from time import perf_counter

import azure.functions as func

try:
    from azure.cosmos import CosmosClient  # type: ignore
except Exception:  # pragma: no cover
    CosmosClient = None  # type: ignore

from src.specs.queue.message import QueueMessage
from src.shared.state import RunStateStore
from src.shared.logging_utils import info as log_info, error as log_error
from src.agents.image_agent_foundry import FoundryImageAgent
from src.specs.agents.image import ImageAgentInput
from src.tools.image_creation_tools import call_function_tool as call_image_tool


bp = func.Blueprint()


def _get_cosmos_container(env_name: str) -> Any:
    conn = os.getenv("COSMOS_DB_CONNECTION_STRING")
    db_name = os.getenv("COSMOS_DB_NAME")
    container_name = os.getenv(env_name)
    if not conn or not db_name or not container_name or CosmosClient is None:
        return None
    client = CosmosClient.from_connection_string(conn)
    db = client.get_database_client(db_name)
    return db.get_container_client(container_name)


def _load_content_caption(content_ref: Optional[str]) -> str:
    if not content_ref:
        return ""
    container = _get_cosmos_container("COSMOS_DB_CONTAINER_POSTS")
    if container is None:
        return ""
    try:
        # Try direct read (partition likely brandId, but we don't have it here). Use query fallback.
        query = "SELECT TOP 1 c FROM c WHERE c.id = @id"
        items = list(
            container.query_items(
                query=query,
                parameters=[{"name": "@id", "value": content_ref}],
                enable_cross_partition_query=True,
            )
        )
        if not items:
            try:
                log_info(None, "cosmos:posts:query_miss", contentRef=content_ref)
            except Exception:
                pass
            return ""
        first = items[0]
        doc = first.get("c") if isinstance(first, dict) and "c" in first else first
        content = (doc or {}).get("content") or {}
        caption = content.get("caption")
        try:
            log_info(None, "cosmos:posts:query_hit", contentRef=content_ref, captionLen=len(caption or ""))
        except Exception:
            pass
        return caption or ""
    except Exception as exc:
        try:
            log_info(None, "cosmos:posts:query_failed", contentRef=content_ref, error=str(exc))
        except Exception:
            pass
        return ""


def _generate_image_via_agent(
    *,
    run_trace_id: str,
    brand_id: str,
    post_plan_id: str,
    content_ref: Optional[str],
) -> dict:
    caption = _load_content_caption(content_ref)
    agent = FoundryImageAgent()
    out = agent.run(ImageAgentInput(brandId=brand_id, postPlanId=post_plan_id, runTraceId=run_trace_id, caption=caption))
    return {"mediaRef": out.mediaRef, "url": out.url, "provider": getattr(out, "provider", None)}


@bp.function_name(name="q_media_generate")
@bp.queue_trigger(
    arg_name="msg",
    queue_name="media-tasks",
    connection="AZURE_STORAGE_CONNECTION_STRING",
)
@bp.queue_output(
    arg_name="publish_queue",
    queue_name="publish-tasks",
    connection="AZURE_STORAGE_CONNECTION_STRING",
)
def q_media_generate(msg: func.QueueMessage, publish_queue: func.Out[str]) -> None:
    start = perf_counter()
    body = msg.get_body().decode("utf-8")
    data = json.loads(body)
    q = QueueMessage(**data)

    log_info(q.runTraceId, "queue:dequeued", queue="media-tasks", messageId=getattr(msg, "id", None))

    # Mark phase start
    RunStateStore.set_status(
        q.runTraceId,
        phase="image",
        status="in_progress",
        brand_id=q.brandId,
        post_plan_id=q.postPlanId,
    )
    log_info(q.runTraceId, "image:start", brandId=q.brandId, postPlanId=q.postPlanId)
    try:
        RunStateStore.add_event(q.runTraceId, phase="image", action="start")  # type: ignore[attr-defined]
    except Exception as exc:
        log_error(q.runTraceId, "run_state:add_event_failed", phase="image", action="start", error=str(exc))

    # Generate, upload, and persist image
    content_ref = (q.refs or {}).get("contentRef") if isinstance(q.refs, dict) else getattr(q.refs, "contentRef", None)
    try:
        result = _generate_image_via_agent(
            run_trace_id=q.runTraceId,
            brand_id=q.brandId,
            post_plan_id=q.postPlanId,
            content_ref=content_ref,
        )
    except Exception as exc:
        # Fallback to direct image generation tool (which handles Azure OpenAI or placeholder)
        tool_resp = call_image_tool(
            "generate_image_from_prompt",
            {
                "brandId": q.brandId,
                "postPlanId": q.postPlanId,
                "runTraceId": q.runTraceId,
                "prompt": _load_content_caption(content_ref),
            },
        )
        res = (tool_resp.get("result") or {}) if isinstance(tool_resp, dict) else {}
        result = {"mediaRef": res.get("mediaRef", ""), "url": res.get("url", ""), "provider": res.get("provider")}
        try:
            RunStateStore.add_event(
                q.runTraceId,
                phase="image",
                action="fallback_generate",
                message=str(exc),
            )  # type: ignore[attr-defined]
        except Exception as exc2:
            log_error(q.runTraceId, "run_state:add_event_failed", phase="image", action="fallback_generate", error=str(exc2))

    try:
        RunStateStore.add_event(
            q.runTraceId,
            phase="image",
            action="agent_output",
            data={"mediaRef": result.get("mediaRef"), "url": result.get("url")},
        )  # type: ignore[attr-defined]
    except Exception as exc:
        log_error(q.runTraceId, "run_state:add_event_failed", phase="image", action="agent_output", error=str(exc))

    # Mark phase complete
    RunStateStore.set_status(
        q.runTraceId,
        phase="image",
        status="completed",
        summary=result,
        brand_id=q.brandId,
        post_plan_id=q.postPlanId,
    )
    duration_ms = int((perf_counter() - start) * 1000)
    log_info(q.runTraceId, "image:completed", durationMs=duration_ms)
    try:
        RunStateStore.add_event(q.runTraceId, phase="image", action="completed")  # type: ignore[attr-defined]
    except Exception as exc:
        log_error(q.runTraceId, "run_state:add_event_failed", phase="image", action="completed", error=str(exc))

    # Enqueue publish
    next_msg = QueueMessage(
        runTraceId=q.runTraceId,
        brandId=q.brandId,
        postPlanId=q.postPlanId,
        step="publish",
        agent="none",
        refs={"contentRef": content_ref, "mediaRef": result["mediaRef"]},
    )
    publish_queue.set(next_msg.model_dump_json())
    log_info(q.runTraceId, "image:enqueued_publish")
    try:
        RunStateStore.add_event(
            q.runTraceId,
            phase="image",
            action="enqueued_next",
            data={"next": "publish-tasks", "step": "publish", "mediaRef": result.get("mediaRef")},
        )  # type: ignore[attr-defined]
    except Exception as exc:
        log_error(q.runTraceId, "run_state:add_event_failed", phase="image", action="enqueued_next", error=str(exc))
