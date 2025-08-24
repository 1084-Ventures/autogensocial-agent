"""
Tool for retrieving brand documents from Cosmos DB
"""
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
from src.shared.cosmos_client import get_cosmos_client
from src.specs.documents.brand_document_spec import BrandDocument
from src.specs.common.errors import ResourceNotFoundError

async def get_brand_tool(brand_id: str) -> Dict[str, Any]:
    """
    Retrieves a brand document from Cosmos DB.
    
    Args:
        brand_id: Unique identifier for the brand to retrieve
        
    Returns:
        Dict with standardized envelope containing the brand document or error
    """
    logging.info(f"Retrieving brand document - Brand ID: {brand_id}")
    
    try:
        cosmos = get_cosmos_client()
        container_name = os.environ.get("COSMOS_DB_CONTAINER_BRAND", "brands")
        item = cosmos.get_item(container_name, brand_id)
        
        if not item:
            raise ResourceNotFoundError("Brand", brand_id)
            
        # Convert Cosmos DB timestamp to datetime
        created_at = datetime.fromtimestamp(item.get('_ts', 0))
        updated_at = datetime.fromtimestamp(item.get('_ts', 0))
        
        # Create BrandDocument
        brand_document = BrandDocument(
            id=item.get('id'),
            created_at=created_at,
            updated_at=updated_at,
            is_active=True,
            name=item.get('name'),
            description=item.get('description'),
            logo_url=item.get('logo_url'),
            website=item.get('website'),
            social_accounts=item.get('social_accounts', {}),
            brand_style=item.get('brand_style', {})
        )
        
        return {
            "status": "completed",
            "result": {
                "document": brand_document.dict(),
                "documentId": brand_id
            },
            "error": None,
            "meta": {
                "durationMs": 0,  # Could add timing if needed
                "container": container_name,
                "documentType": "Brand"
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
        logging.exception(f"Failed to retrieve brand document - Brand ID: {brand_id}")
        return {
            "status": "failed",
            "result": None,
            "error": {
                "code": "BRAND_RETRIEVAL_ERROR",
                "message": str(e)
            },
            "meta": {
                "durationMs": 0
            }
        }
