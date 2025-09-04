from __future__ import annotations

import logging
import os
import time
from functools import lru_cache
from typing import Optional

from azure.cosmos import CosmosClient  # type: ignore

from src.specs.models.tools import (
    ErrorInfo,
    GetBrandRequest,
    GetBrandResponse,
    GetBrandResult,
)
from src.specs.models.domain import BrandDocument
from src.specs.tools_registry import ToolDef


@lru_cache(maxsize=1)
def _get_container():
    conn_str = os.getenv("COSMOS_DB_CONNECTION_STRING")
    db_name = os.getenv("COSMOS_DB_NAME")
    container_name = os.getenv("COSMOS_DB_CONTAINER_BRAND")
    if not (conn_str and db_name and container_name):
        missing = [
            k for k, v in [
                ("COSMOS_DB_CONNECTION_STRING", conn_str),
                ("COSMOS_DB_NAME", db_name),
                ("COSMOS_DB_CONTAINER_BRAND", container_name),
            ]
            if not v
        ]
        raise RuntimeError(
            f"Missing Cosmos env vars for brand lookup: {', '.join(missing)}"
        )
    client = CosmosClient.from_connection_string(conn_str)
    db = client.get_database_client(db_name)
    return db.get_container_client(container_name)


def get_brand(
    req: GetBrandRequest,
    *,
    logger: Optional[logging.Logger] = None,
) -> GetBrandResponse:
    """Fetch a brand document by id from Cosmos DB.

    Uses a cross-partition query to avoid assumptions about the partition key.
    """
    log = logger or logging.getLogger("autogensocial")
    start = time.perf_counter()
    meta = {}

    try:
        cont = _get_container()
        query = "SELECT * FROM c WHERE c.id = @id"
        params = [{"name": "@id", "value": req.brandId}]
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
                "get_brand: not found brandId=%s trace=%s",
                req.brandId,
                req.runTraceId,
            )
            return GetBrandResponse(
                status="failed",
                result=None,
                error=ErrorInfo(code="NotFound", message=f"Brand {req.brandId} not found"),
                meta=meta,
            )

        doc = items[0]
        brand = BrandDocument.model_validate(doc)
        dur_ms = int((time.perf_counter() - start) * 1000)
        meta = {"durationMs": dur_ms}
        log.info(
            "get_brand: found brandId=%s trace=%s",
            req.brandId,
            req.runTraceId,
        )
        return GetBrandResponse(
            status="completed",
            result=GetBrandResult(brand=brand),
            error=None,
            meta=meta,
        )
    except Exception as exc:
        dur_ms = int((time.perf_counter() - start) * 1000)
        meta = {"durationMs": dur_ms}
        log.exception(
            "get_brand: error brandId=%s trace=%s err=%s",
            req.brandId,
            req.runTraceId,
            exc,
        )
        return GetBrandResponse(
            status="failed",
            result=None,
            error=ErrorInfo(code="Exception", message=str(exc)),
            meta=meta,
        )


__all__ = ["get_brand"]

# Tool registry integration

TOOL_DEF = ToolDef(
    name="get_brand",
    description="Retrieve a brand document by id",
    input_model=GetBrandRequest,
    output_model=GetBrandResponse,
)


def execute(args: dict, logger: Optional[logging.Logger] = None) -> GetBrandResponse:
    """Adapter for centralized tool registry: accepts dict args, returns typed response."""
    req = GetBrandRequest(**args)
    return get_brand(req, logger=logger)
