"""
Tool for searching media in the database.
"""
import logging
from typing import List, Dict, Any

from src.shared.cosmos_client import get_cosmos_container


def search_database_media_impl(query: str):
    # Implementation logic here (see below)
    try:
        container = get_cosmos_container('media')
        query_str = f"SELECT * FROM c WHERE CONTAINS(c.tags, '{query}') OR CONTAINS(c.description, '{query}')"
        items = list(container.query_items(
            query=query_str,
            enable_cross_partition_query=True
        ))
        return items
    except Exception as e:
        logging.error(f"Failed to search database media: {str(e)}")
        return []

search_database_media_tool = {
    "name": "search_database_media",
    "description": "Search for media assets in the database using tags and descriptions",
    "parameters": {
        "query": {"type": "string", "description": "The search query to find media assets"}
    },
    "implementation": search_database_media_impl
}

def search_database_media_impl(query: str) -> List[Dict[str, Any]]:
    """
    Search for media in the database based on a query.
    
    Args:
        query (str): The search query
        
    Returns:
        List[Dict[str, Any]]: A list of media items matching the query
    """
    try:
        container = get_cosmos_container('media')
        # TODO: Implement proper search query with parameters
        query_str = f"SELECT * FROM c WHERE CONTAINS(c.tags, '{query}') OR CONTAINS(c.description, '{query}')"
        items = list(container.query_items(
            query=query_str,
            enable_cross_partition_query=True
        ))
        return items
    except Exception as e:
        logging.error(f"Failed to search database media: {str(e)}")
        return []

# Attach the implementation to the tool
