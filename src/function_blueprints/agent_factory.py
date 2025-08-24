"""
Factory module for creating and managing agent instances.
"""

from typing import Optional
import logging
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from src.agents.copywriter_agent import CopywriterAgent
from src.specs.common.trace_logger_spec import TraceLogger

logger = logging.getLogger(__name__)

def create_copywriter_agent(
    project_endpoint: str,
    model_name: str,
    trace_logger: Optional[TraceLogger] = None
) -> CopywriterAgent:
    """
    Create a new CopywriterAgent instance with proper configuration.
    
    Args:
        project_endpoint: Azure AI Foundry project endpoint
        model_name: Model deployment name to use
        trace_logger: Optional TraceLogger instance for detailed logging
        
    Returns:
        CopywriterAgent: A configured agent instance
        
    Raises:
        ValueError: If required configuration is missing
        RuntimeError: If agent creation fails
    """
    try:
        agent = CopywriterAgent(
            project_endpoint=project_endpoint,
            trace_logger=trace_logger,
            credential=DefaultAzureCredential()
        )
        logger.info("Successfully created copywriter agent")
        return agent
    except Exception as e:
        logger.error(f"Failed to create copywriter agent: {str(e)}")
        raise RuntimeError(f"Failed to create copywriter agent: {str(e)}")
