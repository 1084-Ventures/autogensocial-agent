# Azure AI Foundry SDK conventions
import os
from datetime import datetime
from src.shared.cosmos_client import CosmosDBClient
from src.specs.documents.post_plan_document_spec import PostPlanDocument
from azure.ai.agents.models import FunctionTool

def get_post_plan_tool(post_plan_id: str) -> PostPlanDocument:
    """
    Retrieves a PostPlan document from Cosmos DB based on the provided post_plan_id.

    :param post_plan_id: Unique identifier for the post plan to retrieve.
    :return: The retrieved post plan document as a PostPlanDocument.
    """
    cosmos = CosmosDBClient()
    container_name = os.environ.get("COSMOS_DB_CONTAINER_POST_PLANS", "postPlans")
    item = cosmos.get_item(container_name, post_plan_id)
    if not item:
        raise ValueError(f"Post plan with id {post_plan_id} not found.")

    # Convert Cosmos DB timestamp to datetime
    created_at = datetime.fromtimestamp(item.get('_ts', 0))
    updated_at = datetime.fromtimestamp(item.get('_ts', 0))

    # Create PostPlanDocument with required fields
    post_plan_document = PostPlanDocument(
        id=item.get('id'),
        created_at=created_at,
        updated_at=updated_at,
        is_active=True,  # Default to True since it exists in the database
        brand_id=item.get('brand_id'),
        post_plan=item.get('post_plan'),
        status=item.get('status', 'pending'),  # Default to 'pending' if not set
        last_executed_at=item.get('last_executed_at'),
        execution_history=item.get('execution_history', [])
    )
    return post_plan_document

# Register the function as a FunctionTool for Azure AI Foundry agents
get_post_plan_function_tool = FunctionTool(functions={get_post_plan_tool})