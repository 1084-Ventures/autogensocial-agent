"""
Tool for processing copywriter tasks
"""
import logging
from typing import Dict, Any
from src.function_blueprints.agent_factory import create_copywriter_agent
from src.specs.agents.copywriter_agent_spec import CopywriterAgentRequest
import os

async def process_copywriter_task_tool(
    run_trace_id: str,
    brand_document: Dict[str, Any],
    post_plan_document: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process a copywriter task with the given parameters.
    
    Args:
        run_trace_id (str): The trace ID for tracking
        brand_document (Dict[str, Any]): The brand document
        post_plan_document (Dict[str, Any]): The post plan document
        
    Returns:
        Dict[str, Any]: The copywriter response
    """
    logging.info(f"Processing copywriter task - Trace ID: {run_trace_id}")
    
    project_endpoint = os.environ.get("PROJECT_ENDPOINT")
    model_name = os.environ.get("MODEL_DEPLOYMENT_NAME")
    if not project_endpoint or not model_name:
        raise EnvironmentError("PROJECT_ENDPOINT and MODEL_DEPLOYMENT_NAME environment variables must be set.")

    # Create agent
    agent = create_copywriter_agent(
        project_endpoint=project_endpoint,
        model_name=model_name
    )
    
    # Create request
    request = CopywriterAgentRequest(
        brand_document=brand_document,
        post_plan_document=post_plan_document,
        run_trace_id=run_trace_id
    )
    
    # Process content
    response = await agent.create_content(request)
    logging.info(f"Generated content with trace ID: {response.traceId}")
    
    return response.dict()
