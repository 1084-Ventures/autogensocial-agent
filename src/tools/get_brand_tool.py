from typing import Optional, Dict, Any

import os

try:
    from azure.cosmos import CosmosClient, exceptions  # type: ignore
except Exception:  # pragma: no cover
    CosmosClient = None  # type: ignore
    exceptions = None  # type: ignore

from src.specs.common.envelope import ToolResult
from src.shared.logging_utils import info as log_info
from src.specs.tools.data import GetBrandRequest, GetBrandResponse


def _get_container() -> Any:
    """Resolve Cosmos container for brand documents.

    Expects env vars:
    - COSMOS_DB_CONNECTION_STRING
    - COSMOS_DB_NAME
    - COSMOS_DB_CONTAINER_BRAND
    """
    conn = os.getenv("COSMOS_DB_CONNECTION_STRING")
    db_name = os.getenv("COSMOS_DB_NAME")
    container_name = os.getenv("COSMOS_DB_CONTAINER_BRAND")
    if not conn or not db_name or not container_name:
        raise RuntimeError("Missing Cosmos configuration for brand container")
    if CosmosClient is None:
        raise RuntimeError("azure-cosmos package not available")
    client = CosmosClient.from_connection_string(conn)
    db = client.get_database_client(db_name)
    return db.get_container_client(container_name)


def _read_brand_doc(container: Any, brand_id: str) -> Optional[Dict]:
    """Read a brand document, trying direct PK read and then query fallback."""
    # First attempt: direct point-read assuming PK equals brandId
    try:
        item = container.read_item(item=brand_id, partition_key=brand_id)
        doc = dict(item)
        log_info(
            None,
            "cosmos:get_brand:read_item",
            brandId=brand_id,
            docId=str(doc.get("id")),
            type=str(doc.get("type")),
        )
        return doc
    except Exception as exc:
        log_info(None, "cosmos:get_brand:read_item_failed", brandId=brand_id, error=str(exc))

    # Fallback: cross-partition query by id or brandId
    try:
        query = (
            "SELECT TOP 1 c FROM c WHERE c.id = @id OR c.brandId = @id OR c.partitionKey = @id"
        )
        items = list(
            container.query_items(
                query=query,
                parameters=[{"name": "@id", "value": brand_id}],
                enable_cross_partition_query=True,
            )
        )
        if items:
            first = items[0]
            doc = dict(first["c"]) if isinstance(first, dict) and len(first) == 1 and "c" in first else dict(first)
            log_info(
                None,
                "cosmos:get_brand:query_hit",
                brandId=brand_id,
                docId=str(doc.get("id")),
                type=str(doc.get("type")),
            )
            return doc
    except Exception as exc:
        log_info(None, "cosmos:get_brand:query_failed", brandId=brand_id, error=str(exc))

    return None


def run(req: GetBrandRequest) -> GetBrandResponse:
    """Retrieve a brand document by brandId.

    Returns GetBrandResponse with status: "ok" | "not_found" | "error"
    """
    try:
        container = _get_container()
        doc = _read_brand_doc(container, req.brandId)
        if doc is None:
            return GetBrandResponse(status="not_found", document=None)
        return GetBrandResponse(status="ok", document=doc)
    except Exception as exc:  # pragma: no cover - passthrough errors during local dev
        return GetBrandResponse(status="error", document={"message": str(exc)})


def get_brand(brand_id: str) -> GetBrandResponse:
    """Convenience wrapper to call run() with just a brand_id."""
    return run(GetBrandRequest(brandId=brand_id))


# Azure Foundry/OpenAI function tool specification for this tool
FUNCTION_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_brand",
        "description": "Retrieve the brand document by brandId.",
        "parameters": {
            "type": "object",
            "properties": {
                "brandId": {"type": "string", "description": "The brand identifier"},
            },
            "required": ["brandId"],
            "additionalProperties": False,
        },
    },
}


def call_function_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute this tool from a tool-calling runtime and return ToolResult-like dict."""
    try:
        req = GetBrandRequest(**args)
        resp = run(req)
        status = "completed" if resp.status == "ok" else ("pending" if resp.status == "not_found" else "failed")
        return ToolResult(status=status, result={"document": resp.document, "status": resp.status}).model_dump()
    except Exception as exc:
        return ToolResult(status="failed", error={"code": "exception", "message": str(exc)}).model_dump()
