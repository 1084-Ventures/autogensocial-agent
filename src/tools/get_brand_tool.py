# Azure AI Foundry SDK conventions
import os
from src.shared.cosmos_client import CosmosDBClient
from src.specs.tools.get_brand_tool_spec import GetBrandToolRequest, GetBrandToolResponse
from src.specs.documents.brand_document_spec import BrandDocument
from azure.ai.agents.models import FunctionTool

def get_brand_tool(brand_id: str) -> dict:
	"""
	Retrieves a BrandDocument from Cosmos DB based on the provided brand_id.

	:param brand_id: Unique identifier for the brand to retrieve.
	:return: The retrieved brand document as a dict.
	"""
	cosmos = CosmosDBClient()
	container_name = os.environ.get("COSMOS_DB_CONTAINER_BRAND", "brands")
	item = cosmos.get_item(container_name, brand_id)
	if not item:
		raise ValueError(f"Brand with id {brand_id} not found.")
	return item

# Register the function as a FunctionTool for Azure AI Foundry agents
get_brand_function_tool = FunctionTool(functions={get_brand_tool})
