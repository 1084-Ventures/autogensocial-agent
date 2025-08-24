"""
Tool for searching media online.
"""
import logging
from typing import List, Dict, Any
import os
from azure.ai.agents.models import FunctionTool, Parameter
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

search_online_media_tool = FunctionTool(
    name="search_online_media",
    description="Search for media assets online using Azure AI Search",
    parameters=[
        Parameter(name="query", type="string", description="The search query to find media assets online")
    ]
)

def search_online_media_impl(query: str) -> List[Dict[str, Any]]:
    """
    Search for media online based on a query.
    
    Args:
        query (str): The search query
        
    Returns:
        List[Dict[str, Any]]: A list of media items matching the query
    """
    try:
        endpoint = os.environ["AZURE_AISEARCH_ENDPOINT"]
        key = os.environ["AZURE_AISEARCH_KEY"]
        index_name = "media-index"  # This should be configurable

        client = SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(key)
        )

        results = client.search(
            search_text=query,
            select=["id", "url", "title", "description", "tags"],
            top=10
        )
        
        return [dict(result) for result in results]
    except Exception as e:
        logging.error(f"Failed to search online media: {str(e)}")
        return []

# Attach the implementation to the tool
search_online_media_tool.implementation = search_online_media_impl
