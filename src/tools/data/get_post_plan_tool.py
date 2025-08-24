"""
Tool for retrieving post plan documents from Cosmos DB
"""
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
from src.shared.cosmos_client import get_cosmos_client
from src.specs.documents.post_plan_document_spec import PostPlanDocument
from src.specs.common.errors import ResourceNotFoundError

async def get_post_plan_tool(post_plan_id: str) -> Dict[str, Any]:
    """
    Retrieves a post plan document from Cosmos DB.
    
    Args:
        post_plan_id: Unique identifier for the post plan to retrieve
        
    Returns:
        Dict with standardized envelope containing the post plan document or error
    """
    logging.info(f"Retrieving post plan document - Post Plan ID: {post_plan_id}")
    
    try:
        cosmos = get_cosmos_client()
        container_name = os.environ.get("COSMOS_DB_CONTAINER_POST_PLANS", "postPlans")
        item = cosmos.get_item(container_name, post_plan_id)
        
        if not item:
            raise ResourceNotFoundError("PostPlan", post_plan_id)
            
        # Convert Cosmos DB timestamp to datetime
        created_at = datetime.fromtimestamp(item.get('_ts', 0))
        updated_at = datetime.fromtimestamp(item.get('_ts', 0))
        
        # Create PostPlanDocument
        post_plan_document = PostPlanDocument(
            id=item.get('id'),
            created_at=created_at,
            updated_at=updated_at,
            is_active=True,
            brand_id=item.get('brand_id'),
            post_plan=item.get('post_plan'),
            status=item.get('status', 'pending'),
            last_executed_at=item.get('last_executed_at'),
            execution_history=item.get('execution_history', [])
        )
        
        return {
            "status": "completed",
            "result": {
                "document": post_plan_document.dict(),
                "documentId": post_plan_id
            },
            "error": None,
            "meta": {
                "durationMs": 0,
                "container": container_name,
                "documentType": "PostPlan"
            }
        }
        
    except ResourceNotFoundError as e:
        logging.error(f"{e.code}: {str(e)}")
        return {
            "status": "failed",
            "result": None,
            "error": e.to_dict(),
            "meta": {
                "durationMs": 0
            }
        }
    except Exception as e:
        logging.exception(f"Failed to retrieve post plan document - Post Plan ID: {post_plan_id}")
        return {
            "status": "failed",
            "result": None,
            "error": {
                "code": "POST_PLAN_RETRIEVAL_ERROR",
                "message": str(e)
            },
            "meta": {
                "durationMs": 0
            }
        }
