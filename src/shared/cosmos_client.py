"""
Standardized Cosmos DB client implementation with caching and improved error handling
"""
import os
import logging
from functools import lru_cache
from typing import Optional, List, Dict, Any, Union
from azure.cosmos import CosmosClient, exceptions
from azure.cosmos.container import ContainerProxy

class CosmosDBClient:
    def __init__(self):
        self.connection_string = os.environ.get("COSMOS_DB_CONNECTION_STRING")
        self.database_name = os.environ.get("COSMOS_DB_NAME")
        if not self.connection_string or not self.database_name:
            raise ValueError("Missing Cosmos DB connection string or database name in environment variables.")
        self.client = CosmosClient.from_connection_string(self.connection_string)
        self.database = self.client.get_database_client(self.database_name)

    def get_container(self, container_name: str) -> ContainerProxy:
        """Get a container by name, using environment variable override if available"""
        env_container_name = os.environ.get(f"COSMOS_DB_CONTAINER_{container_name.upper()}")
        return self.database.get_container_client(env_container_name or container_name)

    def get_item(
        self,
        container_name: str,
        item_id: str,
        partition_key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get an item by ID with improved error handling and logging
        
        Args:
            container_name: Name of the container
            item_id: ID of the item to retrieve
            partition_key: Optional partition key (defaults to item_id)
            
        Returns:
            The item if found, None if not found
        """
        container = self.get_container(container_name)
        try:
            # First try a query to see if the item exists and get its partition key
            logging.debug(f"Querying for item in container '{container_name}' with id '{item_id}'")
            query = f"SELECT * FROM c WHERE c.id = @id"
            items = list(container.query_items(
                query=query,
                parameters=[{"name": "@id", "value": item_id}],
                enable_cross_partition_query=True
            ))
            
            if items:
                logging.debug(f"Found item via query: {items[0]['id']}")
                return items[0]
            
            # Fallback to direct read if query finds nothing
            logging.debug(f"No items found via query, attempting direct read")
            result = container.read_item(
                item=item_id,
                partition_key=partition_key or item_id
            )
            logging.debug(f"Successfully retrieved item via direct read: {result['id']}")
            return result
            
        except exceptions.CosmosResourceNotFoundError:
            logging.debug(f"Item not found: {item_id}")
            return None
        except Exception as e:
            logging.error(
                "Unexpected error reading item",
                extra={
                    "container": container_name,
                    "itemId": item_id,
                    "error": str(e),
                    "databaseName": self.database_name,
                    "endpoint": self.connection_string.split(';')[0]
                }
            )
            raise

    def query_items(
        self,
        container_name: str,
        query: str,
        parameters: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query items with parameterized queries for safety
        
        Args:
            container_name: Name of the container
            query: The query to execute (use @param syntax for parameters)
            parameters: List of parameter dictionaries with 'name' and 'value'
            
        Returns:
            List of matching items
        """
        container = self.get_container(container_name)
        return list(container.query_items(
            query=query,
            parameters=parameters or [],
            enable_cross_partition_query=True
        ))

    def upsert_item(
        self,
        container_name: str,
        item: Dict[str, Any],
        partition_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create or update an item
        
        Args:
            container_name: Name of the container
            item: The item to upsert
            partition_key: Optional partition key (defaults to item['id'])
            
        Returns:
            The created/updated item
        """
        container = self.get_container(container_name)
        return container.upsert_item(
            body=item,
            partition_key=partition_key or item.get('id')
        )

# Singleton instance with caching
@lru_cache(maxsize=1)
def get_cosmos_client() -> CosmosDBClient:
    """Get or create the singleton CosmosDBClient instance"""
    return CosmosDBClient()

def get_cosmos_container(container_name: str) -> ContainerProxy:
    """
    Get a container by name (convenience function using singleton client)
    
    Args:
        container_name: Name of the container to get
        
    Returns:
        The container proxy
    """
    return get_cosmos_client().get_container(container_name)

	def upsert_item(self, container_name, item):
		container = self.get_container(container_name)
		return container.upsert_item(item)
