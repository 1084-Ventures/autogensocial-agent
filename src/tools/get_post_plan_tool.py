from __future__ import annotations

import logging
import os
import time
from functools import lru_cache
from typing import Optional

from azure.cosmos import CosmosClient  # type: ignore

from src.specs.models.tools import (
    ErrorInfo,
    GetPostPlanRequest,
    GetPostPlanResponse,
    GetPostPlanResult,
)
from src.specs.models.domain import PostPlanDocument
from src.specs.tools_registry import ToolDef


@lru_cache(maxsize=1)
def _get_container():
    conn_str = os.getenv("COSMOS_DB_CONNECTION_STRING")
    db_name = os.getenv("COSMOS_DB_NAME")
    container_name = os.getenv("COSMOS_DB_CONTAINER_POST_PLANS")
    if not (conn_str and db_name and container_name):
        missing = [
            k for k, v in [
                ("COSMOS_DB_CONNECTION_STRING", conn_str),
                ("COSMOS_DB_NAME", db_name),
                ("COSMOS_DB_CONTAINER_POST_PLANS", container_name),
            ]
            if not v
        ]
        raise RuntimeError(
            f"Missing Cosmos env vars for post plan lookup: {', '.join(missing)}"
        )
    client = CosmosClient.from_connection_string(conn_str)
    db = client.get_database_client(db_name)
    return db.get_container_client(container_name)


def get_post_plan(
    req: GetPostPlanRequest,
    *,
    logger: Optional[logging.Logger] = None,
) -> GetPostPlanResponse:
    """Fetch a post plan document by id from Cosmos DB.

    Uses a cross-partition query to avoid assumptions about the partition key.
    """
    log = logger or logging.getLogger("autogensocial")
    start = time.perf_counter()
    meta = {}

    try:
        cont = _get_container()
        query = "SELECT * FROM c WHERE c.id = @id"
        params = [{"name": "@id", "value": req.postPlanId}]
        items = list(
            cont.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True,
            )
        )
        if not items:
            dur_ms = int((time.perf_counter() - start) * 1000)
            meta = {"durationMs": dur_ms}
            log.warning(
                "get_post_plan: not found postPlanId=%s trace=%s",
                req.postPlanId,
                req.runTraceId,
            )
            return GetPostPlanResponse(
                status="failed",
                result=None,
                error=ErrorInfo(
                    code="NotFound", message=f"Post plan {req.postPlanId} not found"
                ),
                meta=meta,
            )

        doc = items[0]
        post_plan = PostPlanDocument.model_validate(doc)
        dur_ms = int((time.perf_counter() - start) * 1000)
        meta = {"durationMs": dur_ms}
        log.info(
            "get_post_plan: found postPlanId=%s trace=%s",
            req.postPlanId,
            req.runTraceId,
        )
        return GetPostPlanResponse(
            status="completed",
            result=GetPostPlanResult(postPlan=post_plan),
            error=None,
            meta=meta,
        )
    except Exception as exc:
        dur_ms = int((time.perf_counter() - start) * 1000)
        meta = {"durationMs": dur_ms}
        log.exception(
            "get_post_plan: error postPlanId=%s trace=%s err=%s",
            req.postPlanId,
            req.runTraceId,
            exc,
        )
        return GetPostPlanResponse(
            status="failed",
            result=None,
            error=ErrorInfo(code="Exception", message=str(exc)),
            meta=meta,
        )


__all__ = ["get_post_plan"]


# Tool registry integration
TOOL_DEF = ToolDef(
    name="get_post_plan",
    description="Retrieve a post plan document by id",
    input_model=GetPostPlanRequest,
    output_model=GetPostPlanResponse,
)


def execute(args: dict, logger: Optional[logging.Logger] = None) -> GetPostPlanResponse:
    req = GetPostPlanRequest(**args)
    return get_post_plan(req, logger=logger)
