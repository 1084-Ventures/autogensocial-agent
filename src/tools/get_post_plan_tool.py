# Azure AI Foundry SDK conventions
import os
from src.shared.cosmos_client import CosmosDBClient
from azure.ai.agents.models import FunctionTool

def get_post_plan_tool(post_plan_id: str) -> dict:
    """
    Retrieves a PostPlan document from Cosmos DB based on the provided post_plan_id.

    :param post_plan_id: Unique identifier for the post plan to retrieve.
    :return: The retrieved post plan document as a dict.
    """
    cosmos = CosmosDBClient()
    container_name = os.environ.get("COSMOS_DB_CONTAINER_POST_PLANS", "postPlans")
    item = cosmos.get_item(container_name, post_plan_id)
    if not item:
        raise ValueError(f"Post plan with id {post_plan_id} not found.")
    return item

# Register the function as a FunctionTool for Azure AI Foundry agents
get_post_plan_function_tool = FunctionTool(functions={get_post_plan_tool})