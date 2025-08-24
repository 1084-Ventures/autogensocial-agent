# Azure AI Foundry SDK conventions
import os
from datetime import datetime
from src.shared.cosmos_client import CosmosDBClient
from src.specs.tools.get_brand_tool_spec import GetBrandToolRequest, GetBrandToolResponse
from src.specs.documents.brand_document_spec import BrandDocument
from azure.ai.agents.models import FunctionTool

def get_brand_tool(brand_id: str) -> BrandDocument:
	"""
	Retrieves a BrandDocument from Cosmos DB based on the provided brand_id.

	:param brand_id: Unique identifier for the brand to retrieve.
	:return: The retrieved brand document as a BrandDocument.
	"""
	cosmos = CosmosDBClient()
	container_name = os.environ.get("COSMOS_DB_CONTAINER_BRAND", "brands")
	item = cosmos.get_item(container_name, brand_id)
	if not item:
		raise ValueError(f"Brand with id {brand_id} not found.")

	# Convert Cosmos DB timestamp to datetime
	created_at = datetime.fromtimestamp(item.get('_ts', 0))
	updated_at = datetime.fromtimestamp(item.get('_ts', 0))
	
	# Create BrandDocument with required fields
	brand_document = BrandDocument(
		id=item.get('id'),
		created_at=created_at,
		updated_at=updated_at,
		is_active=True,  # Default to True since it exists in the database
		name=item.get('name'),
		description=item.get('description'),
		logo_url=item.get('logo_url'),
		website=item.get('website'),
		social_accounts=item.get('social_accounts'),
		brand_style=item.get('brand_style')
	)
	return brand_document

# Register the function as a FunctionTool for Azure AI Foundry agents
get_brand_function_tool = FunctionTool(functions={get_brand_tool})
