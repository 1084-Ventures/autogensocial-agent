# Azure AI Foundry SDK conventions
import os
from src.shared.cosmos_client import CosmosDBClient

from typing import List, Optional, Dict, Any

def get_posts_tool(brand_id: str, post_plan_id: Optional[str] = None, fields: Optional[List[str]] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Retrieves posts for a brand (and optionally a post plan) from Cosmos DB.

    :param brand_id: ID of the brand to filter posts.
    :param post_plan_id: (Optional) ID of the post plan to filter posts.
    :param fields: (Optional) List of fields to include in each post document.
    :param limit: (Optional) Maximum number of posts to return.
    :return: List of post documents (dicts), each containing only the requested fields if specified.
    """
    cosmos = CosmosDBClient()
    container_name = os.environ.get("COSMOS_DB_CONTAINER_POSTS", "posts")
    query = "SELECT * FROM c WHERE c.brand_id = @brand_id"
    parameters = [{"name": "@brand_id", "value": brand_id}]
    if post_plan_id:
        query += " AND c.post_plan_id = @post_plan_id"
        parameters.append({"name": "@post_plan_id", "value": post_plan_id})
    query += " ORDER BY c.created_at DESC"
    items = cosmos.query_items(container_name, query, parameters)
    if limit:
        items = items[:limit]
    if fields:
        filtered_items = []
        for item in items:
            filtered = {field: item.get(field) for field in fields if field in item}
            filtered_items.append(filtered)
        return filtered_items
    return items

# Register the function as a dictionary-based tool for Azure AI Foundry agents
get_posts_function_tool = get_posts_tool