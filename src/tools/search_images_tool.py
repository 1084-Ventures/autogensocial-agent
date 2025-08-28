from typing import Dict, Any, List, Optional
import os
import requests

from src.specs.common.envelope import ToolResult


def _bing_image_search(
    query: str,
    *,
    count: int = 8,
    safe_search: Optional[str] = None,
    license: Optional[str] = None,
) -> List[Dict[str, Any]]:
    key = os.getenv("BING_SEARCH_SUBSCRIPTION_KEY") or os.getenv("AZURE_AISERVICES_KEY")
    endpoint = "https://api.bing.microsoft.com/v7.0/images/search"
    if not key:
        return []
    if safe_search is None:
        safe_search = os.getenv("BING_SAFESEARCH", "Moderate")
    if license is None:
        license = os.getenv("BING_IMAGE_LICENSE")  # e.g., ShareCommercially, ModifyCommercially, Public
    market = os.getenv("BING_MARKET")  # e.g., en-US
    params = {
        "q": query,
        "count": count,
        "safeSearch": safe_search,
        "imageType": "Photo",
        "size": "Large",
    }
    if license:
        params["license"] = license
    if market:
        params["mkt"] = market
    headers = {"Ocp-Apim-Subscription-Key": key}
    try:
        r = requests.get(endpoint, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()
        results = []
        for it in data.get("value", [])[:count]:
            results.append(
                {
                    "url": it.get("contentUrl"),
                    "thumbnail": (it.get("thumbnailUrl") or (it.get("thumbnail", {}) or {}).get("url")),
                    "title": it.get("name"),
                    "hostPage": it.get("hostPageUrl"),
                    "width": it.get("width"),
                    "height": it.get("height"),
                    "encodingFormat": it.get("encodingFormat"),
                    "provider": ((it.get("provider") or [{}])[0]).get("name"),
                    "license": (it.get("insightsMetadata", {}) or {}).get("imageLicense"),
                }
            )
        return results
    except Exception:
        return []


def run(query: str, *, count: int = 8, license: Optional[str] = None, safeSearch: Optional[str] = None) -> Dict[str, Any]:
    items = _bing_image_search(query, count=count, license=license, safe_search=safeSearch)
    status = "completed" if items else "failed"
    return ToolResult(status=status, result={"items": items}).model_dump()


FUNCTION_TOOL: Dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_images",
        "description": "Search the web for candidate images (Bing Image Search)",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for images"},
                "count": {"type": "integer", "minimum": 1, "maximum": 16, "default": 8},
                "license": {
                    "type": "string",
                    "description": "Optional license filter (e.g., ShareCommercially, ModifyCommercially, Public)"
                },
                "safeSearch": {"type": "string", "description": "Safe search level (Off, Moderate, Strict)"},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}


def call_function_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    q = (args or {}).get("query") or ""
    count = int((args or {}).get("count") or 8)
    if not q:
        return ToolResult(status="failed", error={"code": "invalid_args", "message": "query is required"}).model_dump()
    lic = (args or {}).get("license")
    safe = (args or {}).get("safeSearch")
    return run(q, count=count, license=lic, safeSearch=safe)
