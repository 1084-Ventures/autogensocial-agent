# AutogenSocial Agent

A serverless Azure Functions app for automated social media content generation and management.

## Features

- Content Generation: Create engaging social media posts using Azure AI Foundry agents
- Media Generation: Generate and process images for social media posts
- Content Publishing: Queue and manage post publishing
- Queue-based Orchestration: Reliable task processing with retries and error handling
- Observability: Comprehensive logging to Application Insights and Cosmos DB

## Local Development

### Prerequisites

- Python 3.9+
- Azure Functions Core Tools
- Azure CLI
- Visual Studio Code with Azure Functions extension

### Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/1084-Ventures/autogensocial-agent.git
cd autogensocial-agent
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `local.settings.json`:
```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    
    # Azure AI Foundry Configuration
    "PROJECT_ENDPOINT": "your-foundry-project-endpoint",
    "MODEL_DEPLOYMENT_NAME": "your-model-deployment",
    
    # Cosmos DB Configuration
    "COSMOS_DB_CONNECTION_STRING": "your-cosmos-connection-string",
    "COSMOS_DB_NAME": "your-database-name",
    
    # Cosmos DB Containers
    "COSMOS_DB_CONTAINER_BRAND": "brands",
    "COSMOS_DB_CONTAINER_POST_PLANS": "postPlans",
    "COSMOS_DB_CONTAINER_POSTS": "posts",
    "COSMOS_DB_CONTAINER_AGENT_RUNS": "agentRuns",
    
    # Optional: Azure AI Search (if using database media search)
    "AZURE_AISEARCH_ENDPOINT": "your-search-endpoint",
    "AZURE_AISEARCH_KEY": "your-search-key"
  }
}
```

### Running Locally

1. Start Azurite for local storage emulation:
```bash
azurite
```

2. Start the function app:
```bash
func start
```

## Architecture

### Components

- **Agent**: CopywriterAgent - Manages AI Foundry agent interactions and tool registration
- **Functions**: HTTP endpoints and queue triggers for orchestration
- **Tools**: Core business logic implementations with standardized interfaces

### Queue Pipeline

1. `content-tasks`: Content generation queue
2. `media-tasks`: Image generation queue
3. `publish-tasks`: Publishing queue
4. `error-tasks`: Error handling queue

### Observability

- Application Insights logging
- Cosmos DB trace storage (agentRuns container)
- Queue message tracking

## Development Guidelines

1. **Tool Contracts**:
   - All tools must return standardized envelope:
   ```python
   {
     "status": "completed" | "failed",
     "result": {...} | None,
     "error": {"code": str, "message": str} | None,
     "meta": {"durationMs": int, ...}
   }
   ```

2. **Queue Messages**:
   - Keep messages small (pass IDs, not full documents)
   - Include tracing information
   ```python
   {
     "runTraceId": str,
     "brandId": str,
     "postPlanId": str,
     "step": str,
     "previous": {...}  # Optional link to prior step
   }
   ```

3. **Error Handling**:
   - Use proper exception types
   - Log with context
   - Queue error tasks for retry/notification

## Contributing

1. Branch naming: `feature/description` or `fix/description`
2. Commit messages: Clear and descriptive
3. Tests: Required for new features
4. Documentation: Update README and docstrings