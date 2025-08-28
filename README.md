# AutogenSocial Agent

A serverless Azure Functions app for automated social media content generation and management.

## Features

- Content Generation: Create engaging social media posts using Azure AI Foundry Agents SDK
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

4. Login to Azure for local development (for DefaultAzureCredential):
```bash
az login
# If you have multiple tenants/subscriptions:
az account set --subscription "<your-subscription-name-or-id>"
```

5. Create `local.settings.json` (don’t commit secrets):
```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    
    # Storage
    "AZURE_STORAGE_CONNECTION_STRING": "<your-azure-storage-connection-string>",
    # Single source of truth for Functions host as well
    "AzureWebJobsStorage": "%AZURE_STORAGE_CONNECTION_STRING%",

    # Queue names (override to customize without code changes)
    "CONTENT_TASKS_QUEUE": "content-tasks",
    "MEDIA_TASKS_QUEUE": "media-tasks",
    "PUBLISH_TASKS_QUEUE": "publish-tasks",
    # Optional: Application Insights
    "APPLICATIONINSIGHTS_CONNECTION_STRING": "your-appinsights-connection-string",
    
    # Azure AI Foundry Agents (default agent backend)
    # PROJECT_ENDPOINT: From Azure AI Foundry Project (copy the endpoint)
    # MODEL_DEPLOYMENT_NAME: The model deployment configured in your project
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
    
    # Runtime state backend: file (default) or cosmos
    "RUN_STATE_BACKEND": "file",
    
    # Optional: Azure AI Search (if using database media search)
    "AZURE_AISEARCH_ENDPOINT": "your-search-endpoint",
    "AZURE_AISEARCH_KEY": "your-search-key"
  }
}
```

### Running Locally

1. Start the function app:
```bash
func start
```

Notes:
- Queues bind via `AZURE_STORAGE_CONNECTION_STRING`. The Functions host also uses storage via `AzureWebJobsStorage`, which here references `%AZURE_STORAGE_CONNECTION_STRING%` to avoid duplication.
- If you prefer Azurite locally, start it and set:
  - `AZURE_STORAGE_CONNECTION_STRING=UseDevelopmentStorage=true`
  - `AzureWebJobsStorage=UseDevelopmentStorage=true`
  - `azurite --location "$HOME/.azurite" --silent`
  - Avoid storing Azurite data in the repo to prevent file-watcher restarts.

Azure AI Foundry Agents require authentication via `DefaultAzureCredential`. Locally this typically uses your Azure CLI or VS Code login. Ensure `az login` is completed before starting the Functions host.

## Architecture

### Components

- **Agent**: FoundryCopywriterAgent - Manages Azure AI Foundry Agent interactions and tool registration
- **Functions**: HTTP endpoints and queue triggers for orchestration
- **Tools**: Core business logic implementations with standardized interfaces

### Queue Pipeline

1. `CONTENT_TASKS_QUEUE` (default: `content-tasks`): Content generation
2. `MEDIA_TASKS_QUEUE` (default: `media-tasks`): Image generation
3. `PUBLISH_TASKS_QUEUE` (default: `publish-tasks`): Publishing
4. `error-tasks` (optional): Error handling

### Observability

- Application Insights logging
- Cosmos DB trace storage (agentRuns container)
- Queue message tracking

#### Logging

- Logs include `runTraceId` as custom dimensions when supported. To send logs to Application Insights, set `APPLICATIONINSIGHTS_CONNECTION_STRING`. Query examples:
  - `traces | where customDimensions.runTraceId == '<id>'`

#### Run State Storage

- The app supports two backends for run state:
  - `file` (default for local dev): writes JSON under the OS temp directory.
  - `cosmos`: upserts one document per run into the `agentRuns` container using `runTraceId` as the partition key.
- Select via `RUN_STATE_BACKEND=file|cosmos` or leave unset to auto-detect Cosmos when its env vars are present.

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

## Agents

- Default agent implementation uses Azure AI Foundry Agents SDK and function tools for data access:
  - `src/agents/copywriter_agent_foundry.py`
  - Tools are defined per-module and registered as function tools:
    - `src/tools/get_brand_tool.py`
    - `src/tools/get_post_plan_tool.py`

### Required environment for agents

- `PROJECT_ENDPOINT`: AI Foundry project endpoint
- `MODEL_DEPLOYMENT_NAME`: Model deployment within the project
- Azure login for `DefaultAzureCredential` (e.g., `az login` locally)

### Optional persistence

- If `COSMOS_DB_CONNECTION_STRING`, `COSMOS_DB_NAME`, and `COSMOS_DB_CONTAINER_POSTS` are set, generated captions are stored as draft content and referenced by `contentRef`.

## Contributing

1. Branch naming: `feature/description` or `fix/description`
2. Commit messages: Clear and descriptive
3. Tests: Required for new features
4. Documentation: Update README and docstrings
