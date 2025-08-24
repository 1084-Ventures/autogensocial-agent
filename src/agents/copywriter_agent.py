"""
Azure AI Foundry agent specialized in creating engaging social media content.
Implements the sequence defined in autogensocial_http_sequence.mmd.
"""

import os
import json
import time
import logging
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

class AgentError(Exception):
    """Base exception for agent-related errors"""
    pass

class ConfigurationError(AgentError):
    """Raised when there's an issue with agent configuration"""
    pass

class ToolError(AgentError):
    """Raised when there's an issue with tool execution"""
    pass

class ServiceError(AgentError):
    """Raised when there's an issue with external service communication"""
    pass

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import CodeInterpreterTool, FunctionTool
from azure.core.exceptions import ResourceNotFoundError, ServiceRequestError
from azure.core.credentials import TokenCredential
from azure.core.pipeline.policies import RetryPolicy, ThrottlingRetryPolicy
from azure.core.pipeline.transport import RequestsTransport
from functools import lru_cache

from src.tools.get_posts_tool import get_posts_tool
from src.tools.search_online_media_tool import search_online_media_tool
from src.tools.search_database_media_tool import search_database_media_tool
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
        
        # Validate configuration
        self._validate_config()
        
        # Initialize tools
        self.code_interpreter = CodeInterpreterTool()
        self.get_posts_tool = FunctionTool(functions={get_posts_tool})
        self.search_online_media_tool = FunctionTool(functions={search_online_media_tool})
        self.search_database_media_tool = FunctionTool(functions={search_database_media_tool})
        
        # Configure policies
        self.retry_policy = RetryPolicy(
            retry_total=3,
            retry_read=3,
            retry_status=3,
            retry_backoff_factor=0.5
        )
        
        self.throttling_policy = ThrottlingRetryPolicy(
            max_attempts=5,
            retry_backoff_factor=2
        )
        
        # Configure transport with policies
        self.transport = RequestsTransport(
            policies=[self.retry_policy, self.throttling_policy]
        )
        
        # Initialize rate limiting
        self.request_semaphore = asyncio.Semaphore(10)  # Max 10 concurrent requests
        
    def _validate_config(self) -> None:
        """
        Validates the agent's configuration settings.
        Raises ConfigurationError if any required settings are missing or invalid.
        """
        required_settings = {
            "PROJECT_ENDPOINT": self.project_endpoint,
            "MODEL_DEPLOYMENT_NAME": self.model_name
        }
        
        missing_settings = [k for k, v in required_settings.items() if not v]
        if missing_settings:
            raise ConfigurationError(f"Missing required settings: {', '.join(missing_settings)}")
            
    async def _validate_tools(self) -> None:
        """
        Validates that all required tools are available and properly configured.
        Raises ToolError if any tool is not available or misconfigured.
        """
        required_tools = [
            (self.get_posts_tool, "get_posts_tool"),
            (self.search_online_media_tool, "search_online_media_tool"),
            (self.search_database_media_tool, "search_database_media_tool")
        ]
        
        errors: List[str] = []
        for tool, name in required_tools:
            if not tool or not hasattr(tool, 'definitions'):
                errors.append(f"Tool {name} is not properly configured")
                
        if errors:
            raise ToolError("\n".join(errors))
            
    async def check_health(self) -> Tuple[bool, str]:
        """
        Performs a comprehensive health check of the agent and its dependencies.
        
        Returns:
            Tuple[bool, str]: (is_healthy, status_message)
        """
        try:
            # Validate configuration
            self._validate_config()
            
            # Validate tools
            await self._validate_tools()
            
            # Check service connection
            agent = await self._get_or_create_agent()
            if not agent:
                return False, "Failed to initialize or connect to agent"
            
            return True, "Agent is healthy and ready"
            
        except ConfigurationError as e:
            return False, f"Configuration error: {str(e)}"
        except ToolError as e:
            return False, f"Tool error: {str(e)}"
        except ServiceError as e:
            return False, f"Service error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error during health check: {str(e)}"
            
    @lru_cache(maxsize=32)
    async def _get_agent_cached(self, agent_name: str):
        """
        Cached version of agent retrieval to improve performance.
        
        Args:
            agent_name: Name of the agent to retrieve
            
        Returns:
            The agent instance
        """
        try:
            return await self.project_client.agents.get_agent(agent_name)
        except Exception as e:
            raise ServiceError(f"Failed to retrieve agent: {str(e)}")
            
    async def _track_metrics(self, operation: str, duration: float, metadata: Dict[str, Any] = None) -> None:
        """
        Track operation metrics for monitoring and optimization.
        
        Args:
            operation: Name of the operation being tracked
            duration: Duration of the operation in seconds
            metadata: Additional metadata about the operation
        """
        if self.trace_logger:
            await self.trace_logger.log_event(
                "metrics",
                {
                    "operation": operation,
                    "duration": duration,
                    "metadata": metadata or {}
                }
            )
        
    async def create_content(self, request: CopywriterAgentRequest) -> CopywriterAgentResponse:
        """
        Process a content creation request using the AI Foundry agent.
        Follows the sequence in autogensocial_http_sequence.mmd.
        
        Args:
            request: CopywriterAgentRequest containing brand and post plan info
            
        Returns:
            CopywriterAgentResponse with generated content
            
        Raises:
            ConfigurationError: If agent is not properly configured
            ToolError: If there's an issue with tool execution
            ServiceError: If there's an issue with external service communication
        """
        start_time = time.time()
        
        # Perform health check
        is_healthy, status = await self.check_health()
        if not is_healthy:
            raise ServiceError(f"Agent is not healthy: {status}")
        
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
                    
                duration = time.time() - start_time
                metadata = {
                    "agent_id": agent.id,
                    "thread_id": thread.id,
                    "run_id": run.id,
                    "tools_used": [tool.name for tool in run.tools_used] if hasattr(run, 'tools_used') else [],
                    "duration": duration
                }
                
                await self._track_metrics("create_content", duration, metadata)
                
                return CopywriterAgentResponse(
                    success=True,
                    message=success_msg,
                    traceId=request.run_trace_id,
                    post_content=post_content,
                    metadata=metadata
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
                create_agent_args = {
                    "model": self.model_name,
                    "name": AGENT_CONFIG["name"],
                    "description": AGENT_CONFIG["description"],
                    "instructions": AGENT_CONFIG["instructions"],
                    "tools": [
                        self.get_posts_tool.definitions,
                        self.search_online_media_tool.definitions,
                        self.search_database_media_tool.definitions,
                        self.code_interpreter.definitions
                    ]
                }
                
                # Apply retry policy
                agent = await self.project_client.agents.create_agent(
                    **create_agent_args,
                    retry_policy=self.retry_policy
                )
                
                logger.info(f"Created new copywriter agent with ID: {agent.id}")
                return agent
                
        except ServiceRequestError as e:
            logger.error(f"Service connection error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Failed to get/create copywriter agent: {str(e)}")
            raise
