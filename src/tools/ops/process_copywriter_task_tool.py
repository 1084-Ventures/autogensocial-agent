"""
Tool for processing copywriter tasks with standardized response envelope
"""
import logging
import os
import time
from typing import Dict, Any
from src.agents.copywriter_agent import CopywriterAgent
from src.specs.agents.copywriter_agent_spec import CopywriterAgentRequest
from src.specs.common.errors import (
    ConfigurationError,
    ContentGenerationError,
    ResourceNotFoundError
)
from src.tools.data.get_brand_tool import get_brand_tool
from src.tools.data.get_post_plan_tool import get_post_plan_tool

async def process_copywriter_task_impl(
    run_trace_id: str,
    brand_id: str,
    post_plan_id: str
) -> Dict[str, Any]:
    """
    Process a copywriter task with the given parameters.
    
    Args:
        run_trace_id (str): The trace ID for tracking
        brand_id (str): The ID of the brand document to use
        post_plan_id (str): The ID of the post plan document to use
        
    Returns:
        Dict[str, Any]: Response envelope with status, result, error, and metadata
    
    Raises:
        ConfigurationError: If required environment variables are missing
        ResourceNotFoundError: If brand or post plan documents are not found
        ContentGenerationError: If content generation fails
    """
    logging.info(f"Processing copywriter task - Trace ID: {run_trace_id}")
    start_time = time.time()
    
    try:
        # Validate configuration
        project_endpoint = os.environ.get("PROJECT_ENDPOINT")
        if not project_endpoint:
            raise ConfigurationError("PROJECT_ENDPOINT environment variable must be set")
            
        # Initialize agent
        agent = CopywriterAgent(project_endpoint=project_endpoint)
        
        # Retrieve documents
        brand_result = await get_brand_tool(brand_id)
        if not brand_result or brand_result.get("error"):
            raise ResourceNotFoundError("Brand", brand_id)
            
        post_plan_result = await get_post_plan_tool(post_plan_id)
        if not post_plan_result or post_plan_result.get("error"):
            raise ResourceNotFoundError("PostPlan", post_plan_id)
            
        # Create request
        request = CopywriterAgentRequest(
            brand_document=brand_result["document"],
            post_plan_document=post_plan_result["document"],
            run_trace_id=run_trace_id
        )
        
        # Generate content
        response = await agent.create_content(request)
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Return standardized envelope
        return {
            "status": "completed",
            "result": {
                "contentRef": response.postContentId,
                "contentType": response.contentType,
                "brandId": brand_id,
                "postPlanId": post_plan_id
            },
            "error": None,
            "meta": {
                "durationMs": duration_ms,
                "promptTokens": response.metrics.get("promptTokens", 0),
                "completionTokens": response.metrics.get("completionTokens", 0),
                "totalTokens": response.metrics.get("totalTokens", 0)
            }
        }
        
    except (ConfigurationError, ResourceNotFoundError) as e:
        logging.error(f"{e.code}: {str(e)} - Trace ID: {run_trace_id}")
        return {
            "status": "failed",
            "result": None,
            "error": e.to_dict(),
            "meta": {
                "durationMs": int((time.time() - start_time) * 1000)
            }
        }
    except Exception as e:
        logging.exception(f"Content generation failed - Trace ID: {run_trace_id}")
        error = ContentGenerationError(str(e), details={
            "brandId": brand_id,
            "postPlanId": post_plan_id
        })
        return {
            "status": "failed",
            "result": None,
            "error": error.to_dict(),
            "meta": {
                "durationMs": int((time.time() - start_time) * 1000)
            }
        }
