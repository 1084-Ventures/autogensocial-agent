"""
Azure AI Foundry agent specialized in creating engaging social media content.
Implements the sequence defined in autogensocial_http_sequence.mmd.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import CodeInterpreterTool, FunctionTool
from azure.core.exceptions import ResourceNotFoundError, ServiceRequestError
from azure.core.credentials import TokenCredential

from src.tools.get_posts_tool import get_posts_tool
from src.specs.agents.copywriter_agent_spec import CopywriterAgentRequest, CopywriterAgentResponse
from src.specs.agents.copywriter_agent_instructions import AGENT_CONFIG, ADDITIONAL_INSTRUCTIONS
from src.specs.tools.get_posts_tool_spec import GetPostsResponse
from src.specs.documents.post_document_spec import PostContent, PostMediaItem
from src.specs.common.trace_logger_spec import TraceLogger

# Configure logging
logger = logging.getLogger(__name__)

class CopywriterAgent:
    """
    Azure AI Foundry agent specialized in creating engaging social media content.
    Implements the sequence defined in autogensocial_http_sequence.mmd.
    """
    
    def __init__(self, project_endpoint: str = None, trace_logger: Optional[TraceLogger] = None, credential: Optional[TokenCredential] = None):
        """
        Initialize the CopywriterAgent with Azure AI Foundry configuration.
        
        Args:
            project_endpoint: Azure AI Foundry project endpoint. If None, uses PROJECT_ENDPOINT env var.
            trace_logger: Optional TraceLogger instance for detailed logging
            credential: Optional TokenCredential for authentication. If None, uses DefaultAzureCredential
        """
        self.project_endpoint = project_endpoint or os.getenv("PROJECT_ENDPOINT")
        if not self.project_endpoint:
            raise ValueError("PROJECT_ENDPOINT must be provided")
            
        self.model_name = os.getenv("MODEL_DEPLOYMENT_NAME")
        if not self.model_name:
            raise ValueError("MODEL_DEPLOYMENT_NAME must be provided")
        
        self.trace_logger = trace_logger
        self.credential = credential or DefaultAzureCredential()
            
        # Initialize AI Project Client with Azure authentication
        self.project_client = AIProjectClient(
            endpoint=self.project_endpoint,
            credential=self.credential
        )
        
        # Initialize tools
        self.code_interpreter = CodeInterpreterTool()
        self.get_posts_tool = FunctionTool(functions={get_posts_tool})
        
    async def create_content(self, request: CopywriterAgentRequest) -> CopywriterAgentResponse:
        """
        Process a content creation request using the AI Foundry agent.
        Follows the sequence in autogensocial_http_sequence.mmd.
        
        Args:
            request: CopywriterAgentRequest containing brand and post plan info
            
        Returns:
            CopywriterAgentResponse with generated content
        """
        if self.trace_logger and request.run_trace_id:
            await self.trace_logger.log_event(request.run_trace_id, "Starting content creation")
            
        try:
            # Get or create the agent
            agent = await self._get_or_create_agent()
            
            # Create a thread for this conversation
            thread = await self.project_client.agents.threads.create()
            if self.trace_logger and request.run_trace_id:
                await self.trace_logger.log_event(request.run_trace_id, f"Created thread {thread.id}")
            
            # Add the request context as a system message
            context_message = {
                "brand": request.brand_document.dict(),
                "post_plan": request.post_plan_document.dict(),
                "previous_posts": request.previous_posts.dict() if request.previous_posts else None
            }
            
            await self.project_client.agents.messages.create(
                thread_id=thread.id,
                role="system",
                content=json.dumps(context_message, indent=2)
            )
            
            # Run the agent with the content request
            run = await self.project_client.agents.runs.create_and_process(
                thread_id=thread.id,
                agent_id=agent.id,
                additional_instructions=ADDITIONAL_INSTRUCTIONS
            )
            
            if run.status == "failed":
                error_msg = f"Agent run failed: {run.last_error}"
                if self.trace_logger and request.run_trace_id:
                    await self.trace_logger.log_event(request.run_trace_id, error_msg, level="ERROR")
                return CopywriterAgentResponse(
                    success=False,
                    message=error_msg,
                    traceId=request.run_trace_id
                )
            
            # Get the agent's response
            messages = await self.project_client.agents.messages.list(thread_id=thread.id)
            agent_messages = [msg for msg in messages if msg.role == "assistant"]
            
            if not agent_messages:
                error_msg = "No response received from agent"
                if self.trace_logger and request.run_trace_id:
                    await self.trace_logger.log_event(request.run_trace_id, error_msg, level="ERROR")
                return CopywriterAgentResponse(
                    success=False,
                    message=error_msg,
                    traceId=request.run_trace_id
                )
            
            # Parse and validate the response
            try:
                response_content = json.loads(agent_messages[-1].content)
                post_content = PostContent(**response_content.get("post_content", {}))
                
                success_msg = "Successfully generated content"
                if self.trace_logger and request.run_trace_id:
                    await self.trace_logger.log_event(request.run_trace_id, success_msg)
                    
                return CopywriterAgentResponse(
                    success=True,
                    message=success_msg,
                    traceId=request.run_trace_id,
                    post_content=post_content,
                    metadata={
                        "agent_id": agent.id,
                        "thread_id": thread.id,
                        "run_id": run.id,
                        "tools_used": [tool.name for tool in run.tools_used] if hasattr(run, 'tools_used') else []
                    }
                )
            except Exception as e:
                error_msg = f"Failed to parse agent response: {str(e)}"
                if self.trace_logger and request.run_trace_id:
                    await self.trace_logger.log_event(request.run_trace_id, error_msg, level="ERROR")
                return CopywriterAgentResponse(
                    success=False,
                    message=error_msg,
                    traceId=request.run_trace_id
                )
                
        except ServiceRequestError as e:
            error_msg = f"Service connection error: {str(e)}"
            if self.trace_logger and request.run_trace_id:
                await self.trace_logger.log_event(request.run_trace_id, error_msg, level="ERROR")
            return CopywriterAgentResponse(
                success=False,
                message=error_msg,
                traceId=request.run_trace_id
            )
        except Exception as e:
            error_msg = f"Content creation failed: {str(e)}"
            if self.trace_logger and request.run_trace_id:
                await self.trace_logger.log_event(request.run_trace_id, error_msg, level="ERROR")
            return CopywriterAgentResponse(
                success=False,
                message=error_msg,
                traceId=request.run_trace_id
            )
            
    async def _get_or_create_agent(self) -> Any:
        """
        Gets existing agent or creates a new one with proper configuration.
        Uses retry logic for resilience.
        
        Returns:
            Any: The Azure AI Foundry agent instance
            
        Raises:
            ServiceRequestError: If service connection fails
            Exception: If agent creation fails
        """
        try:
            # Try to get existing agent
            try:
                agent = await self.project_client.agents.get_agent(AGENT_CONFIG["name"])
                logger.info("Found existing copywriter agent")
                return agent
            except ResourceNotFoundError:
                logger.info("Creating new copywriter agent")
                
                # Create new agent with tools
                agent = await self.project_client.agents.create_agent(
                    model=self.model_name,
                    name=AGENT_CONFIG["name"],
                    description=AGENT_CONFIG["description"],
                    instructions=AGENT_CONFIG["instructions"],
                    tools=[
                        self.get_posts_tool.definitions,
                        self.code_interpreter.definitions
                    ]
                )
                logger.info(f"Created new copywriter agent with ID: {agent.id}")
                return agent
                
        except ServiceRequestError as e:
            logger.error(f"Service connection error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to get/create copywriter agent: {str(e)}")
            raise
