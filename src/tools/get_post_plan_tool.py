from typing import Optional, Dict, Any

import os

try:
    from azure.cosmos import CosmosClient, exceptions  # type: ignore
except Exception:  # pragma: no cover
    CosmosClient = None  # type: ignore
    exceptions = None  # type: ignore

from src.specs.common.envelope import ToolResult
from src.shared.logging_utils import info as log_info
from src.specs.tools.data import GetPostPlanRequest, GetPostPlanResponse


def _get_container() -> Any:
    """Resolve Cosmos container for post plan documents.

    Expects env vars:
    - COSMOS_DB_CONNECTION_STRING
    - COSMOS_DB_NAME
    - COSMOS_DB_CONTAINER_POST_PLANS
    """
    conn = os.getenv("COSMOS_DB_CONNECTION_STRING")
    db_name = os.getenv("COSMOS_DB_NAME")
    container_name = os.getenv("COSMOS_DB_CONTAINER_POST_PLANS")
    if not conn or not db_name or not container_name:
        raise RuntimeError("Missing Cosmos configuration for post plan container")
    if CosmosClient is None:
        raise RuntimeError("azure-cosmos package not available")
    client = CosmosClient.from_connection_string(conn)
    db = client.get_database_client(db_name)
    return db.get_container_client(container_name)


def _read_post_plan_doc(container: Any, brand_id: str, post_plan_id: str) -> Optional[Dict]:
    """Read a post plan document by id (PK is brandId for point-read)."""
    # First attempt: direct point-read assuming PK is brandId
    try:
        item = container.read_item(item=post_plan_id, partition_key=brand_id)
        doc = dict(item)
        try:
            log_info(
                None,
                "cosmos:get_post_plan:read_item",
                brandId=brand_id,
                docId=str(doc.get("id")),
                type=str(doc.get("type")),
            )
        except Exception:
            pass
        return doc
    except Exception as exc:
        try:
            log_info(None, "cosmos:get_post_plan:read_item_failed", brandId=brand_id, postPlanId=post_plan_id, error=str(exc))
        except Exception:
            pass

    # Fallback: cross-partition query by id + brandId
    try:
        query = (
            "SELECT TOP 1 c FROM c WHERE c.id = @id AND (c.brandId = @brand OR c.partitionKey = @brand)"
        )
        items = list(
            container.query_items(
                query=query,
                parameters=[
                    {"name": "@id", "value": post_plan_id},
                    {"name": "@brand", "value": brand_id},
                ],
                enable_cross_partition_query=True,
            )
        )
        if items:
            first = items[0]
            doc = dict(first["c"]) if isinstance(first, dict) and len(first) == 1 and "c" in first else dict(first)
            try:
                log_info(
                    None,
                    "cosmos:get_post_plan:query_hit",
                    brandId=brand_id,
                    postPlanId=post_plan_id,
                    docId=str(doc.get("id")),
                    type=str(doc.get("type")),
                )
            except Exception:
                pass
            return doc
    except Exception as exc:
        try:
            log_info(None, "cosmos:get_post_plan:query_failed", brandId=brand_id, postPlanId=post_plan_id, error=str(exc))
        except Exception:
            pass

    return None


def run(req: GetPostPlanRequest) -> GetPostPlanResponse:
    """Retrieve a post plan document by brandId + postPlanId.

    Returns GetPostPlanResponse with status: "ok" | "not_found" | "error"
    """
    try:
        container = _get_container()
        doc = _read_post_plan_doc(container, req.brandId, req.postPlanId)
        if doc is None:
            return GetPostPlanResponse(status="not_found", document=None)
        return GetPostPlanResponse(status="ok", document=doc)
    except Exception as exc:  # pragma: no cover
        return GetPostPlanResponse(status="error", document={"message": str(exc)})


def get_post_plan(brand_id: str, post_plan_id: str) -> GetPostPlanResponse:
    """Convenience wrapper to call run() with just ids."""
    return run(GetPostPlanRequest(brandId=brand_id, postPlanId=post_plan_id))


# Azure Foundry/OpenAI function tool specification for this tool
FUNCTION_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_post_plan",
        "description": "Retrieve a post plan document by brandId and postPlanId.",
        "parameters": {
            "type": "object",
            "properties": {
                "brandId": {"type": "string", "description": "The brand identifier"},
                "postPlanId": {"type": "string", "description": "The post plan identifier"},
            },
            "required": ["brandId", "postPlanId"],
            "additionalProperties": False,
        },
    },
}


def call_function_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute this tool from a tool-calling runtime and return ToolResult-like dict."""
    try:
        req = GetPostPlanRequest(**args)
        resp = run(req)
        status = "completed" if resp.status == "ok" else ("pending" if resp.status == "not_found" else "failed")
        return ToolResult(status=status, result={"document": resp.document, "status": resp.status}).model_dump()
    except Exception as exc:
        return ToolResult(status="failed", error={"code": "exception", "message": str(exc)}).model_dump()
