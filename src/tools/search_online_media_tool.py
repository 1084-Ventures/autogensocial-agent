"""
Tool for searching media online.
"""
import logging
from typing import List, Dict, Any
import os
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

def search_online_media_tool(query: str) -> List[Dict[str, Any]]:
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
