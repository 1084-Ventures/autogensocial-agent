"""
Tool for searching media in the database.
"""
import logging
from typing import List, Dict, Any
from azure.ai.agents.models import FunctionTool, Parameter
from src.shared.cosmos_client import get_cosmos_container

search_database_media_tool = FunctionTool(
    name="search_database_media",
    description="Search for media assets in the database using tags and descriptions",
    parameters=[
        Parameter(name="query", type="string", description="The search query to find media assets")
    ]
)

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
search_database_media_tool.implementation = search_database_media_impl
