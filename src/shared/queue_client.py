"""
Azure Storage Queue utilities
"""
import os
from azure.storage.queue import QueueClient
from azure.core.exceptions import ResourceExistsError
import logging

def get_queue_client(queue_name: str) -> QueueClient:
    """
    Get or create a queue client for the specified queue.
    
    Args:
        queue_name (str): Name of the queue
        
    Returns:
        QueueClient: Azure Storage Queue client
    """
    conn_str = os.environ.get("AzureWebJobsStorage")
    if not conn_str:
        raise EnvironmentError("AzureWebJobsStorage connection string not found")
        
    queue_client = QueueClient.from_connection_string(
        conn_str=conn_str,
        queue_name=queue_name
    )
    
    try:
        queue_client.create_queue()
        logging.info(f"Created queue: {queue_name}")
    except ResourceExistsError:
        pass
    except Exception as e:
        logging.error(f"Error creating queue {queue_name}: {str(e)}")
        raise
        
    return queue_client
