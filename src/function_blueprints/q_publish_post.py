import json
import os
import uuid
from datetime import datetime, timezone
from time import perf_counter
import azure.functions as func

try:
    from azure.cosmos import CosmosClient  # type: ignore
except Exception:  # pragma: no cover
    CosmosClient = None  # type: ignore

from src.specs.queue.message import QueueMessage
from src.shared.state import RunStateStore
from src.shared.logging_utils import info as log_info, error as log_error


bp = func.Blueprint()


def _get_cosmos_container(env_name: str):
    conn = os.getenv("COSMOS_DB_CONNECTION_STRING")
    db_name = os.getenv("COSMOS_DB_NAME")
    container_name = os.getenv(env_name)
    if not conn or not db_name or not container_name or CosmosClient is None:
        return None
    client = CosmosClient.from_connection_string(conn)
    db = client.get_database_client(db_name)
    return db.get_container_client(container_name)


def _persist_publish(
    *,
    run_trace_id: str,
    brand_id: str,
    post_plan_id: str,
    content_ref: str,
    media_ref: str,
) -> dict:
    post_id = f"post-{uuid.uuid4().hex[:12]}"
    published_at = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": post_id,
        "partitionKey": brand_id,
        "type": "publishedPost",
        "brandId": brand_id,
        "postPlanId": post_plan_id,
        "runTraceId": run_trace_id,
        "publishedAtUtc": published_at,
        "contentRef": content_ref,
        "mediaRef": media_ref,
        "status": "published",
    }
    container = _get_cosmos_container("COSMOS_DB_CONTAINER_POSTS")
    if container is not None:
        try:
            container.upsert_item(doc)
            try:
                log_info(run_trace_id, "cosmos:posts:upsert_published", postId=post_id, brandId=brand_id)
            except Exception:
                pass
        except Exception as exc:
            try:
                log_error(run_trace_id, "cosmos:posts:upsert_failed", postId=post_id, error=str(exc))
            except Exception:
                pass
    return {"postId": post_id, "publishedAtUtc": published_at, "contentRef": content_ref, "mediaRef": media_ref}


@bp.function_name(name="q_publish_post")
@bp.queue_trigger(
    arg_name="msg",
    queue_name="publish-tasks",
    connection="AZURE_STORAGE_CONNECTION_STRING",
)
def q_publish_post(msg: func.QueueMessage) -> None:
    start = perf_counter()
    body = msg.get_body().decode("utf-8")
    data = json.loads(body)
    q = QueueMessage(**data)

    log_info(q.runTraceId, "queue:dequeued", queue="publish-tasks", messageId=getattr(msg, "id", None))

    # Mark phase start
    RunStateStore.set_status(
        q.runTraceId,
        phase="publish",
        status="in_progress",
        brand_id=q.brandId,
        post_plan_id=q.postPlanId,
    )
    log_info(q.runTraceId, "publish:start", brandId=q.brandId, postPlanId=q.postPlanId)
    try:
        RunStateStore.add_event(q.runTraceId, phase="publish", action="start")  # type: ignore[attr-defined]
    except Exception as exc:
        log_error(q.runTraceId, "run_state:add_event_failed", phase="publish", action="start", error=str(exc))

    # Publish
    content_ref = (q.refs or {}).get("contentRef") if isinstance(q.refs, dict) else getattr(q.refs, "contentRef", None)
    media_ref = (q.refs or {}).get("mediaRef") if isinstance(q.refs, dict) else getattr(q.refs, "mediaRef", None)
    result = _persist_publish(
        run_trace_id=q.runTraceId,
        brand_id=q.brandId,
        post_plan_id=q.postPlanId,
        content_ref=content_ref,
        media_ref=media_ref,
    )
    try:
        RunStateStore.add_event(
            q.runTraceId,
            phase="publish",
            action="published",
            data={"postId": result.get("postId"), "contentRef": content_ref, "mediaRef": media_ref},
        )  # type: ignore[attr-defined]
    except Exception as exc:
        log_error(q.runTraceId, "run_state:add_event_failed", phase="publish", action="published", error=str(exc))

    # Mark complete
    RunStateStore.set_status(
        q.runTraceId,
        phase="publish",
        status="completed",
        summary=result,
        brand_id=q.brandId,
        post_plan_id=q.postPlanId,
    )
    duration_ms = int((perf_counter() - start) * 1000)
    log_info(q.runTraceId, "publish:completed", postId=result.get("postId"), durationMs=duration_ms)
    try:
        RunStateStore.add_event(
            q.runTraceId,
            phase="publish",
            action="completed",
            data={"postId": result.get("postId")},
        )  # type: ignore[attr-defined]
    except Exception as exc:
        log_error(q.runTraceId, "run_state:add_event_failed", phase="publish", action="completed", error=str(exc))
