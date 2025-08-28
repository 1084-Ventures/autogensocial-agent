import io
import os
import uuid
from typing import Dict, Any, Optional

import requests

from src.media.image_generator import generate_placeholder_image
from src.shared.blob_store import upload_bytes
from src.specs.common.envelope import ToolResult
from src.shared.logging_utils import info as log_info

try:
    from azure.cosmos import CosmosClient  # type: ignore
except Exception:  # pragma: no cover
    CosmosClient = None  # type: ignore


def _get_cosmos_container(env_name: str):
    conn = os.getenv("COSMOS_DB_CONNECTION_STRING")
    db_name = os.getenv("COSMOS_DB_NAME")
    container_name = os.getenv(env_name)
    if not conn or not db_name or not container_name or CosmosClient is None:
        return None
    client = CosmosClient.from_connection_string(conn)
    db = client.get_database_client(db_name)
    return db.get_container_client(container_name)


def _persist_media(*, brand_id: str, post_plan_id: str, run_trace_id: str, url: str, provider: str, meta: Dict[str, Any]) -> Dict[str, Any]:
    media_id = f"media-{uuid.uuid4().hex}"
    container_client = _get_cosmos_container("COSMOS_DB_CONTAINER_MEDIA")
    if container_client is not None:
        doc = {
            "id": media_id,
            "partitionKey": brand_id,
            "type": "generatedMedia",
            "brandId": brand_id,
            "postPlanId": post_plan_id,
            "runTraceId": run_trace_id,
            "media": {
                "url": url,
                "format": meta.get("format", "png"),
                "meta": meta,
                "provider": provider,
            },
        }
        try:
            container_client.upsert_item(doc)
            try:
                log_info(run_trace_id, "cosmos:media:upsert", mediaId=media_id, brandId=brand_id, postPlanId=post_plan_id, provider=provider)
            except Exception:
                pass
        except Exception as exc:
            try:
                log_info(run_trace_id, "cosmos:media:upsert_failed", mediaId=media_id, error=str(exc))
            except Exception:
                pass
    return {"mediaRef": media_id, "url": url, "provider": provider}


def persist_image_from_url(args: Dict[str, Any]) -> Dict[str, Any]:
    brand_id = (args or {}).get("brandId")
    post_plan_id = (args or {}).get("postPlanId")
    run_trace_id = (args or {}).get("runTraceId") or uuid.uuid4().hex
    url = (args or {}).get("url")
    if not (brand_id and post_plan_id and url):
        return ToolResult(status="failed", error={"code": "invalid_args", "message": "brandId, postPlanId, url required"}).model_dump()
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        content_type = r.headers.get("Content-Type", "image/jpeg").split(";")[0]
        ext = "png" if "png" in content_type else ("jpg" if "jpeg" in content_type or "jpg" in content_type else "bin")
        container = os.getenv("PUBLIC_BLOB_CONTAINER", "media")
        blob_name = f"external/{run_trace_id}.{ext}"
        uploaded = upload_bytes(container=container, blob_name=blob_name, data=r.content, content_type=content_type)
        meta = {
            "sourceUrl": url,
            "size": len(r.content),
            "format": ext,
            # Optional passthrough metadata from search result for auditability
            "license": (args or {}).get("license"),
            "title": (args or {}).get("title"),
            "hostPage": (args or {}).get("hostPage"),
            "provider": (args or {}).get("provider"),
            "thumbnail": (args or {}).get("thumbnail"),
            "width": (args or {}).get("width"),
            "height": (args or {}).get("height"),
        }
        result = _persist_media(brand_id=brand_id, post_plan_id=post_plan_id, run_trace_id=run_trace_id, url=uploaded, provider="web", meta=meta)
        return ToolResult(status="completed", result=result).model_dump()
    except Exception as exc:
        return ToolResult(status="failed", error={"code": "download_failed", "message": str(exc)}).model_dump()


def generate_image_from_prompt(args: Dict[str, Any]) -> Dict[str, Any]:
    brand_id = (args or {}).get("brandId")
    post_plan_id = (args or {}).get("postPlanId")
    run_trace_id = (args or {}).get("runTraceId") or uuid.uuid4().hex
    prompt = (args or {}).get("prompt") or (args or {}).get("caption") or ""
    if not (brand_id and post_plan_id):
        return ToolResult(status="failed", error={"code": "invalid_args", "message": "brandId, postPlanId required"}).model_dump()

    # Optional Azure OpenAI image generation via REST; fallback to placeholder
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_KEY")
    image_deployment = os.getenv("AZURE_OPENAI_IMAGE_DEPLOYMENT_NAME", "gpt-image-1")
    image_api_version = os.getenv("AZURE_OPENAI_IMAGE_API_VERSION", "2024-06-01")
    container = os.getenv("PUBLIC_BLOB_CONTAINER", "media")

    image_bytes: Optional[bytes] = None
    provider = "placeholder"
    meta: Dict[str, Any] = {}

    if endpoint and api_key and image_deployment:
        try:
            # Azure OpenAI Images REST API
            url = f"{endpoint}/openai/images/generations:submit?api-version={image_api_version}"
            headers = {"api-key": api_key, "Content-Type": "application/json"}
            body = {"model": image_deployment, "prompt": prompt or "Generate a simple social graphic", "size": "1024x1024"}
            resp = requests.post(url, headers=headers, json=body, timeout=60)
            resp.raise_for_status()
            # The :submit endpoint is long-running; poll the operation-location
            op_url = resp.headers.get("operation-location")
            if op_url:
                for _ in range(40):  # ~40 * 1.5s = 60s
                    pr = requests.get(op_url, headers={"api-key": api_key}, timeout=15)
                    pr.raise_for_status()
                    pdata = pr.json()
                    status = (pdata.get("status") or "").lower()
                    if status in ("succeeded", "completed"):  # payload shape: result.data[0].b64_json
                        data = ((pdata.get("result") or {}).get("data") or [])
                        if data:
                            import base64
                            b64 = data[0].get("b64_json")
                            if b64:
                                image_bytes = base64.b64decode(b64)
                                provider = "azure-openai"
                                break
                    elif status in ("failed", "canceled", "cancelled"):
                        break
                    import time
                    time.sleep(1.5)
        except Exception:
            image_bytes = None

    if image_bytes is None:
        image_bytes, ig_meta = generate_placeholder_image(prompt or f"{brand_id}:{post_plan_id}")
        meta.update(ig_meta)

    blob_name = f"generated/{run_trace_id}.png"
    uploaded_url = upload_bytes(container=container, blob_name=blob_name, data=image_bytes, content_type="image/png")
    meta.setdefault("format", "png")
    result = _persist_media(brand_id=brand_id, post_plan_id=post_plan_id, run_trace_id=run_trace_id, url=uploaded_url, provider=provider, meta=meta)
    return ToolResult(status="completed", result=result).model_dump()


FUNCTION_TOOLS: Dict[str, Any] = {
    "persist_image_from_url": {
        "type": "function",
        "function": {
            "name": "persist_image_from_url",
            "description": "Download an image URL, upload to blob, and record mediaRef in Cosmos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "brandId": {"type": "string"},
                    "postPlanId": {"type": "string"},
                    "runTraceId": {"type": "string"},
                    "url": {"type": "string"},
                    "license": {"type": "string"},
                    "title": {"type": "string"},
                    "hostPage": {"type": "string"},
                    "provider": {"type": "string"},
                    "thumbnail": {"type": "string"},
                    "width": {"type": "number"},
                    "height": {"type": "number"},
                },
                "required": ["brandId", "postPlanId", "url"],
                "additionalProperties": False,
            },
        },
    },
    "generate_image_from_prompt": {
        "type": "function",
        "function": {
            "name": "generate_image_from_prompt",
            "description": "Generate a new image (Azure OpenAI if configured, else placeholder), upload and persist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "brandId": {"type": "string"},
                    "postPlanId": {"type": "string"},
                    "runTraceId": {"type": "string"},
                    "prompt": {"type": "string"},
                    "caption": {"type": "string"},
                },
                "required": ["brandId", "postPlanId"],
                "additionalProperties": False,
            },
        },
    },
}


def call_function_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "persist_image_from_url":
        return persist_image_from_url(args)
    if name == "generate_image_from_prompt":
        return generate_image_from_prompt(args)
    return ToolResult(status="failed", error={"code": "unknown_tool", "message": name}).model_dump()
