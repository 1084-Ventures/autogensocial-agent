````instructions
## Copilot Instructions for Azure Functions with AI Foundry Multi-Agent Workflow (Python v2)

### 1. Python Naming Conventions (PEP 8)
- Modules & files: `lowercase_with_underscores`
- Packages & folders: `lowercase_with_underscores`
- Classes: `CapitalizedWords` (PascalCase)
- Functions & methods: `lowercase_with_underscores`
- Variables: `lowercase_with_underscores`
- Constants: `ALL_UPPERCASE_WITH_UNDERSCORES`
- Private members: `_single_leading_underscore`
- Magic methods: `__double_leading_and_trailing_underscores__`

### 2. Azure AI Foundry Agent Concepts
- Agent: Custom AI that uses AI models with tools
- Tool: Extensions that enhance agent capabilities (e.g., knowledge bases, web search)
- Thread: Conversation session between agent and user, storing messages
- Message: Content created by agent or user (text, images, files)
- Run: Activation of an agent based on thread contents
- Run Step: Detailed list of steps taken by agent during a run

### 2.1 Required Dependencies
```txt
azure-functions
azure-ai-projects
azure-identity
```

### 2.2 Environment Setup
Required environment variables:
- `PROJECT_ENDPOINT`: Azure AI Foundry project endpoint (format: https://<AIFoundryResourceName>.services.ai.azure.com/api/projects/<ProjectName>)
- `MODEL_DEPLOYMENT_NAME`: Name of the deployed model in Azure AI Foundry

### 3. Project Structure
```
<project_root>/
 | - .venv/                    # Virtual environment (not deployed)
 | - function_app.py          # Main entry point with function app instance
 | - agents/                  # AI Foundry agent definitions
 | | - __init__.py
 | | - content_agent.py      # Content generation agent
 | | - review_agent.py       # Content review agent
 | - shared_code/            # Shared utilities and helpers
 | | - __init__.py
 | | - cosmos_client.py      # Database operations
 | | - ai_clients.py         # AI service clients
 | - tools/                  # Custom agent tools
 | | - __init__.py
 | | - search_tool.py        # Web search capabilities
 | | - media_tool.py         # Media handling
 | - tests/                  # Unit tests (not deployed)
 | - .funcignore            # Deployment exclusions
 | - host.json             # Runtime configuration
 | - local.settings.json   # Local settings (not deployed)
 | - requirements.txt      # Python package dependencies
```

### 4. Example Implementation

```python
# agents/content_agent.py
import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import CodeInterpreterTool

class ContentAgent:
    def __init__(self):
        # Initialize AI Project Client
        project_endpoint = os.getenv("PROJECT_ENDPOINT")
        self.project_client = AIProjectClient(
            endpoint=project_endpoint,
            credential=DefaultAzureCredential()
        )
        
        # Initialize tools
        self.code_interpreter = CodeInterpreterTool()
    
    def create_agent(self):
        """Create an AI Foundry agent instance."""
        with self.project_client:
            agent = self.project_client.agents.create_agent(
                model=os.getenv("MODEL_DEPLOYMENT_NAME"),
                name="content-agent",
                instructions="You help create engaging social media content...",
                tools=self.code_interpreter.definitions
            )
            return agent.id
    
    def process_content_request(self, agent_id: str, prompt: str):
        """Process a content creation request."""
        try:
            # Create conversation thread
            thread = self.project_client.agents.threads.create()
            
            # Add user message
            message = self.project_client.agents.messages.create(
                thread_id=thread.id,
                role="user",
                content=prompt
            )
            
            # Execute agent run
            run = self.project_client.agents.runs.create_and_process(
                thread_id=thread.id,
                agent_id=agent_id
            )
            
            if run.status == "failed":
                raise Exception(f"Agent run failed: {run.last_error}")
            
            # Get agent responses
            messages = self.project_client.agents.messages.list(thread_id=thread.id)
            responses = [msg for msg in messages if msg.role == "assistant"]
            
            return responses[-1].content if responses else None
            
        except Exception as e:
            raise Exception(f"Content processing failed: {str(e)}")

# function_app.py
import azure.functions as func
import logging
from agents.content_agent import ContentAgent

app = func.FunctionApp()

@app.function_name(name="process_content")
@app.route(route="content", auth_level=func.AuthLevel.FUNCTION)
def process_content(req: func.HttpRequest) -> func.HttpResponse:
    """Process content creation request using AI Foundry agent."""
    try:
        # Initialize agent
        content_agent = ContentAgent()
        agent_id = content_agent.create_agent()
        
        # Get request data
        data = req.get_json()
        prompt = data.get("prompt")
        
        if not prompt:
            return func.HttpResponse(
                "No prompt provided",
                status_code=400
            )
        
        # Process request
        result = content_agent.process_content_request(agent_id, prompt)
        
        return func.HttpResponse(
            body=json.dumps({"content": result}),
            mimetype="application/json"
        )
        
    except ValueError as ve:
        return func.HttpResponse(str(ve), status_code=400)
    except Exception as e:
        logging.error(f"Content processing failed: {str(e)}")
        return func.HttpResponse(
            "Internal server error",
            status_code=500
        )
```

### 5. Agent Testing
```python
# tests/test_content_agent.py
import unittest
import os
from unittest.mock import patch, MagicMock
from agents.content_agent import ContentAgent

class TestContentAgent(unittest.TestCase):
    def setUp(self):
        self.agent = ContentAgent()
        
    @patch('azure.ai.projects.AIProjectClient')
    def test_create_agent(self, mock_client):
        # Mock the agent creation
        mock_agent = MagicMock()
        mock_agent.id = "test-agent-id"
        mock_client.return_value.agents.create_agent.return_value = mock_agent
        
        # Test agent creation
        agent_id = self.agent.create_agent()
        self.assertEqual(agent_id, "test-agent-id")
        
    @patch('azure.ai.projects.AIProjectClient')
    def test_process_content_request(self, mock_client):
        # Mock thread and message creation
        mock_thread = MagicMock()
        mock_thread.id = "test-thread-id"
        mock_client.return_value.agents.threads.create.return_value = mock_thread
        
        # Mock run creation and processing
        mock_run = MagicMock()
        mock_run.status = "completed"
        mock_client.return_value.agents.runs.create_and_process.return_value = mock_run
        
        # Mock message responses
        mock_message = MagicMock()
        mock_message.role = "assistant"
        mock_message.content = "Test response"
        mock_client.return_value.agents.messages.list.return_value = [mock_message]
        
        # Test content processing
        response = self.agent.process_content_request("test-agent-id", "Test prompt")
        self.assertEqual(response, "Test response")
```

### 6. Best Practices for AI Foundry Integration

1. Authentication and Security:
   - Use DefaultAzureCredential for authentication
   - Ensure proper RBAC roles (Azure AI User role at project scope)
   - Use managed identities in Azure
   - Keep credentials secure and never in code

2. Error Handling:
   - Always check run.status for failures
   - Implement proper error handling and logging
   - Return appropriate HTTP status codes
   - Log agent runs for debugging

3. Resource Management:
   - Use context managers (with statements)
   - Clean up resources (delete unused agents)
   - Monitor thread storage usage
   - Implement proper connection management

4. Performance:
   - Cache frequently used agent instances
   - Implement proper timeout handling
   - Use async operations for long-running tasks
   - Monitor agent response times

5. Testing:
   - Mock AI Foundry client responses
   - Test error scenarios
   - Validate agent configurations
   - Test tool integrations

### 7. Environment Configuration
```json
{
    "IsEncrypted": false,
    "Values": {
        "FUNCTIONS_WORKER_RUNTIME": "python",
        "PYTHON_ENABLE_WORKER_EXTENSIONS": "1",
        "APPLICATIONINSIGHTS_CONNECTION_STRING": "...",
        "PROJECT_ENDPOINT": "https://<AIFoundryResourceName>.services.ai.azure.com/api/projects/<ProjectName>",
        "MODEL_DEPLOYMENT_NAME": "gpt-35-turbo",
        "AZURE_TENANT_ID": "...",
        "AZURE_SUBSCRIPTION_ID": "..."
    }
}
```

### 8. Common AI Foundry Tools
1. Code Interpreter:
   - Execute code snippets
   - Generate visualizations
   - Process data

2. Knowledge Base:
   - Ground responses in custom data
   - Access proprietary information
   - Ensure accurate responses

3. Web Search:
   - Access current information
   - Verify facts
   - Enhance responses

4. Custom Tools:
   - Connect to external APIs
   - Access specific data sources
   - Extend agent capabilities

### 9. Monitoring and Observability
1. Application Insights:
   - Track agent performance
   - Monitor success rates
   - Analyze response times

2. Log Analytics:
   - Review agent runs
   - Debug failures
   - Track usage patterns

3. Metrics:
   - Monitor resource usage
   - Track costs
   - Analyze patterns

---
Follow these instructions to ensure your Azure Functions with AI Foundry agents are secure, maintainable, and follow the latest best practices for the Python v2 programming model.
