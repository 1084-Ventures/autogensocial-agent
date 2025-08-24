# Standardized Cosmos DB client implementation

import os
import time
import logging
import backoff
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional, List, Dict, Any, Union
from azure.cosmos import CosmosClient, exceptions
from azure.cosmos.container import ContainerProxy
from src.specs.common.errors import ConfigurationError, ResourceNotFoundError

class RetryableCosmosError(Exception):
    """Indicates a Cosmos DB operation that should be retried"""
    pass

class CosmosDBClient:
    # Max retries and timeout configuration
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 0.1  # 100ms
    MAX_RETRY_DELAY = 2.0      # 2s
    OPERATION_TIMEOUT = 10.0    # 10s
    
    def __init__(self):
        """Initialize the Cosmos DB client with connection settings and retry policy"""
        self.connection_string = os.environ.get("COSMOS_DB_CONNECTION_STRING")
        self.database_name = os.environ.get("COSMOS_DB_NAME")
        
        if not self.connection_string or not self.database_name:
            raise ConfigurationError("Missing Cosmos DB connection string or database name")
            
        self.client = CosmosClient.from_connection_string(
            self.connection_string,
            retry_total=self.MAX_RETRIES
        )
        self.database = self.client.get_database_client(self.database_name)

    @backoff.on_exception(
        backoff.expo,
        RetryableCosmosError,
        max_tries=MAX_RETRIES,
        max_time=OPERATION_TIMEOUT
    )
    def get_container(self, container_name: str) -> ContainerProxy:
        """
        Get a container by name with environment variable override
        
        Args:
            container_name: Base name of the container
            
        Returns:
            ContainerProxy for the container
            
        Raises:
            ConfigurationError: If container name resolution fails
            RetryableCosmosError: If operation should be retried
        """
        try:
            env_container_name = os.environ.get(f"COSMOS_DB_CONTAINER_{container_name.upper()}")
            actual_name = env_container_name or container_name
            return self.database.get_container_client(actual_name)
            
        except exceptions.CosmosHttpResponseError as e:
            if e.status_code in (429, 503):  # Too Many Requests or Service Unavailable
                raise RetryableCosmosError(f"Retriable error getting container: {str(e)}")
            raise

    @backoff.on_exception(
        backoff.expo,
        RetryableCosmosError,
        max_tries=MAX_RETRIES,
        max_time=OPERATION_TIMEOUT
    )
    def get_item(
        self,
        container_name: str,
        item_id: str,
        partition_key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get an item by ID with improved error handling and retries
        
        Args:
            container_name: Name of the container
            item_id: ID of the item to retrieve
            partition_key: Optional partition key (defaults to item_id)
            
        Returns:
            The item if found, None if not found
            
        Raises:
            ResourceNotFoundError: If item does not exist
            RetryableCosmosError: If operation should be retried
            Exception: For other errors
        """
        start_time = time.time()
        container = self.get_container(container_name)
        
        try:
            # First try a query to find the item and its partition key
            logging.debug(f"Querying for item '{item_id}' in container '{container_name}'")
            query = "SELECT * FROM c WHERE c.id = @id"
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

    @backoff.on_exception(
        backoff.expo,
        RetryableCosmosError,
        max_tries=MAX_RETRIES,
        max_time=OPERATION_TIMEOUT
    )
    def delete_item(
        self,
        container_name: str,
        item_id: str,
        partition_key: Optional[str] = None
    ) -> None:
        """
        Delete an item by ID with retries
        
        Args:
            container_name: Name of the container
            item_id: ID of the item to delete
            partition_key: Optional partition key (defaults to item_id)
            
        Raises:
            RetryableCosmosError: If operation should be retried
            Exception: For other errors
        """
        start_time = time.time()
        container = self.get_container(container_name)
        
        if partition_key is None:
            partition_key = item_id
            
        try:
            container.delete_item(item=item_id, partition_key=partition_key)
            logging.debug(f"Successfully deleted item '{item_id}' in {time.time() - start_time:.2f}s")
            
        except exceptions.CosmosResourceNotFoundError:
            # Item doesn't exist, treat as success but log for tracking
            logging.info(f"Item '{item_id}' not found during delete - already deleted")
            
        except exceptions.CosmosHttpResponseError as e:
            if e.status_code in [429, 503]:  # Rate limited or service unavailable
                error_msg = f"Retryable error deleting item '{item_id}': {e}"
                logging.warning(error_msg)
                raise RetryableCosmosError(error_msg) from e
            logging.error(f"Error deleting item '{item_id}': {e}")
            raise
            
        except Exception as e:
            logging.error(f"Unexpected error deleting item '{item_id}': {e}")
            raise
            
    @backoff.on_exception(
        backoff.expo,
        RetryableCosmosError,
        max_tries=MAX_RETRIES,
        max_time=OPERATION_TIMEOUT
    )
    def bulk_delete_items(
        self,
        container_name: str,
        items: List[Dict[str, str]]
    ) -> None:
        """
        Delete multiple items in bulk with retries and batching
        
        Args:
            container_name: Name of the container
            items: List of dictionaries containing 'id' and optionally 'partitionKey'
            
        Raises:
            RetryableCosmosError: If operation should be retried
            Exception: For other errors
        """
        if not items:
            return
            
        start_time = time.time()
        container = self.get_container(container_name)
        batch_size = 100  # Cosmos DB batch size limit
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_start = time.time()
            
            try:
                for item in batch:
                    item_id = item['id']
                    partition_key = item.get('partitionKey', item_id)
                    
                    try:
                        container.delete_item(item=item_id, partition_key=partition_key)
                    except exceptions.CosmosResourceNotFoundError:
                        # Item already deleted, continue with next
                        logging.info(f"Item '{item_id}' not found during bulk delete - skipping")
                        continue
                        
                logging.debug(
                    f"Successfully deleted batch of {len(batch)} items in {time.time() - batch_start:.2f}s"
                )
                
            except exceptions.CosmosHttpResponseError as e:
                if e.status_code in [429, 503]:  # Rate limited or service unavailable
                    error_msg = f"Retryable error in bulk delete operation: {e}"
                    logging.warning(error_msg)
                    raise RetryableCosmosError(error_msg) from e
                logging.error(f"Error during bulk delete operation: {e}")
                raise
                
            except Exception as e:
                logging.error(f"Unexpected error during bulk delete operation: {e}")
                raise
                
        logging.info(
            f"Bulk delete completed: {len(items)} items processed in {time.time() - start_time:.2f}s"
        )
            
    @backoff.on_exception(
        backoff.expo,
        RetryableCosmosError,
        max_tries=MAX_RETRIES,
        max_time=OPERATION_TIMEOUT
    )
    def list_items(
        self,
        container_name: str,
        max_count: Optional[int] = None,
        continuation_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List items in a container with optional pagination
        
        Args:
            container_name: Name of the container
            max_count: Optional maximum number of items to return
            continuation_token: Optional token from a previous request for pagination
            
        Returns:
            Dictionary containing:
                - items: List of items retrieved
                - continuation_token: Token for getting next page (if more items exist)
                - total_count: Total number of items retrieved
            
        Raises:
            RetryableCosmosError: If operation should be retried
            Exception: For other errors
        """
        start_time = time.time()
        container = self.get_container(container_name)
        items = []
        
        try:
            query = "SELECT * FROM c"
            
            # Set up query options
            options = {
                "enable_cross_partition_query": True,
                "max_item_count": max_count,
                "continuation_token": continuation_token
            }
            
            # Remove None values
            options = {k: v for k, v in options.items() if v is not None}
            
            # Execute query
            results = container.query_items(query=query, **options)
            items = list(results)
            
            # Get continuation token if available
            response_continuation = results.continuation_token
            
            logging.debug(
                f"Retrieved {len(items)} items from container '{container_name}' "
                f"in {time.time() - start_time:.2f}s"
            )
            
            return {
                "items": items,
                "continuation_token": response_continuation,
                "total_count": len(items)
            }
            
        except exceptions.CosmosHttpResponseError as e:
            if e.status_code in [429, 503]:  # Rate limited or service unavailable
                error_msg = f"Retryable error listing items: {e}"
                logging.warning(error_msg)
                raise RetryableCosmosError(error_msg) from e
            logging.error(f"Error listing items: {e}")
            raise
            
        except Exception as e:
            logging.error(f"Unexpected error listing items: {e}")
            raise
