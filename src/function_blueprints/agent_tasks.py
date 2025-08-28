import uuid
from datetime import datetime, timezone
from typing import Optional

from src.agents.copywriter_agent_foundry import FoundryCopywriterAgent
from src.agents.image_agent_foundry import FoundryImageAgent
from src.specs.agents.copywriter import CopywriterInput
from src.specs.agents.image import ImageAgentInput
from src.specs.agents.publish import PublishInput, PublishOutput
from src.shared.cosmos_utils import get_cosmos_container
from src.shared.logging_utils import info as log_info, error as log_error


def generate_content_with_agent(run_trace_id: str, brand_id: str, post_plan_id: str) -> dict:
    agent = FoundryCopywriterAgent()
    out = agent.run(
        CopywriterInput(
            brandId=brand_id, postPlanId=post_plan_id, runTraceId=run_trace_id
        )
    )
    return {
        "contentRef": out.contentRef,
        "caption": out.caption,
        "hashtags": out.hashtags,
    }


def _load_content_caption(content_ref: Optional[str]) -> str:
    if not content_ref:
        return ""
    container = get_cosmos_container("COSMOS_DB_CONTAINER_POSTS")
    if container is None:
        return ""
    try:
        query = "SELECT TOP 1 c FROM c WHERE c.id = @id"
        items = list(
            container.query_items(
                query=query,
                parameters=[{"name": "@id", "value": content_ref}],
                enable_cross_partition_query=True,
            )
        )
        if not items:
            log_info(None, "cosmos:posts:query_miss", contentRef=content_ref)
            return ""
        first = items[0]
        doc = first.get("c") if isinstance(first, dict) and "c" in first else first
        content = (doc or {}).get("content") or {}
        caption = content.get("caption")
        log_info(
            None,
            "cosmos:posts:query_hit",
            contentRef=content_ref,
            captionLen=len(caption or ""),
        )
        return caption or ""
    except Exception as exc:
        log_info(
            None,
            "cosmos:posts:query_failed",
            contentRef=content_ref,
            error=str(exc),
        )
        return ""


def generate_image_via_agent(
    *,
    run_trace_id: str,
    brand_id: str,
    post_plan_id: str,
    content_ref: Optional[str],
) -> dict:
    caption = _load_content_caption(content_ref)
    agent = FoundryImageAgent()
    out = agent.run(
        ImageAgentInput(
            brandId=brand_id,
            postPlanId=post_plan_id,
            runTraceId=run_trace_id,
            caption=caption,
        )
    )
    return {
        "mediaRef": out.mediaRef,
        "url": out.url,
        "provider": getattr(out, "provider", None),
    }


def persist_publish(data: PublishInput) -> PublishOutput:
    post_id = f"post-{uuid.uuid4().hex[:12]}"
    published_at = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": post_id,
        "partitionKey": data.brandId,
        "type": "publishedPost",
        "brandId": data.brandId,
        "postPlanId": data.postPlanId,
        "runTraceId": data.runTraceId,
        "publishedAtUtc": published_at,
        "contentRef": data.contentRef,
        "mediaRef": data.mediaRef,
        "status": "published",
    }
    container = get_cosmos_container("COSMOS_DB_CONTAINER_POSTS")
    if container is not None:
        try:
            container.upsert_item(doc)
            log_info(
                data.runTraceId,
                "cosmos:posts:upsert_published",
                postId=post_id,
                brandId=data.brandId,
            )
        except Exception as exc:
            log_error(
                data.runTraceId,
                "cosmos:posts:upsert_failed",
                postId=post_id,
                error=str(exc),
            )
    return PublishOutput(
        postId=post_id,
        publishedAtUtc=published_at,
        contentRef=data.contentRef,
        mediaRef=data.mediaRef,
    )
