# AutogenSocial Agent

A serverless Azure Functions app for automated social media content generation and management.

## Features

 - Content Generation: Create engaging social media posts using Azure AI Foundry Agents SDK
 - Media Generation: Generate and process images for social media posts
 - Content Publishing: Managed publishing workflow
 - Durable Orchestration: Statefully coordinate content, media, and publish steps
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
- Durable Functions require a storage account. The Functions host uses `AzureWebJobsStorage`, which in the sample settings references `%AZURE_STORAGE_CONNECTION_STRING%` to avoid duplication.
- If you prefer Azurite locally, start it and set:
  - `AZURE_STORAGE_CONNECTION_STRING=UseDevelopmentStorage=true`
  - `AzureWebJobsStorage=UseDevelopmentStorage=true`
  - `azurite --location "$HOME/.azurite" --silent`
  - Avoid storing Azurite data in the repo to prevent file-watcher restarts.

Azure AI Foundry Agents require authentication via `DefaultAzureCredential`. Locally this typically uses your Azure CLI or VS Code login. Ensure `az login` is completed before starting the Functions host.

## Architecture

### Components

- **Agent**: FoundryCopywriterAgent - Manages Azure AI Foundry Agent interactions and tool registration
- **Functions**: HTTP endpoints and durable orchestrations for workflow coordination
- **Tools**: Core business logic implementations with standardized interfaces
- **Specs**: Contracts and schemas under `src/specs/` (`openapi.yaml`, `workflow.yaml`, `schemas/`, `tools.yaml`)

### Durable Pipeline

The app uses a single durable orchestrator (`autogensocial_orchestrator`) started via `POST /autogensocial/orchestrate` to coordinate the workflow. Best practices applied to the orchestration include:

- The HTTP starter triggers the orchestrator and returns the durable `instanceId` so clients can poll for progress.
- The orchestrator remains deterministic and performs no direct I/O; all side effects are delegated to activity functions. Input is validated via Pydantic models at HTTP, orchestration, and activity boundaries.
- Activity functions are idempotent and accept only the identifiers they need (brand, plan, content, media, etc.).
- Durable Functions automatically checkpoints state after each activity, allowing the workflow to resume if the host restarts.
- The orchestrator sets a `customStatus` with `phase`, and defaults `runTraceId` to the Durable `instanceId` for correlation when not supplied.

The orchestrator calls three activities in sequence:

1. `generate_content` – produce caption and hashtags and persist a `contentRef`.
2. `generate_image` – create media for the content and save a `mediaRef`.
3. `publish_post` – persist the final post document.

Clients query `/check_task_status` with the returned `instanceId` to monitor the workflow.

### Observability

 - Application Insights logging
 - Cosmos DB trace storage (agentRuns container)
 - Durable instance tracking

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

2. **Activity Payloads**:
   - Keep payloads small (pass IDs, not full documents)
   - Include tracing information
   ```python
   {
     "runTraceId": str,
     "brandId": str,
     "postPlanId": str
   }
   ```

3. **Error Handling**:
  - Use proper exception types
  - Log with context
  - Surface errors through the run state store

## Agents

- Default agent implementation uses Azure AI Foundry Agents SDK and function tools for data access:
  - `src/agents/copywriter_agent.py`
  - Tools are modular and auto-discovered from `src/tools/*_tool.py`.
    - Each tool module must export:
      - `TOOL_DEF`: `ToolDef(name, description, input_model, output_model)`
      - `execute(args: dict, logger=None)` returning the typed response model
    - Example tools:
      - `src/tools/get_brand_tool.py`
      - `src/tools/get_post_plan_tool.py`

### Required environment for agents

- `PROJECT_ENDPOINT`: AI Foundry project endpoint
- `MODEL_DEPLOYMENT_NAME`: Model deployment within the project
- `COPYWRITER_AGENT_NAME` (optional): logical name used when auto-creating or resolving the agent (default: `AutogenSocialCopywriter`).
- Azure login for `DefaultAzureCredential` (e.g., `az login` locally)

Resolution: The app resolves the agent ID by checking the registry (Cosmos DB when configured, otherwise a local temp file) using `COPYWRITER_AGENT_NAME`; if not found, it searches by name and persists it, or creates a new agent and persists it. When it finds an existing agent, it best-effort updates the agent to include the function tools (`get_brand`, `get_post_plan`). The `COPYWRITER_AGENT_ID` environment variable is not used.

Instructions storage:
- Canonical source is stored in Cosmos DB (same container as the agent registry) as an `AgentConfig` document keyed by the logical name. Fields include `agentId`, `instructions`, optional `tools`, etc.
- On first run, if `instructions` are missing, the app seeds them from a local file under `src/agents/instructions/<logical_name>.md` (e.g., `copywriter.md`) and writes them to Cosmos.
- On ensure, the app compares Cosmos instructions to the remote agent and updates the agent if they drift.

### Optional persistence

- If `COSMOS_DB_CONNECTION_STRING`, `COSMOS_DB_NAME`, and `COSMOS_DB_CONTAINER_POSTS` are set, generated captions are stored as draft content and referenced by `contentRef`.
- Agent ID persistence: If `COSMOS_DB_CONNECTION_STRING`, `COSMOS_DB_NAME`, and `COSMOS_DB_CONTAINER_AGENTS` are set, the app persists the mapping `{ logicalName -> agentId }` in Cosmos. Otherwise, it stores it in a local temp file (e.g., `/tmp/autogensocial/agents.json`).

## Contributing

1. Branch naming: `feature/description` or `fix/description`
2. Commit messages: Clear and descriptive
3. Tests: Required for new features
4. Documentation: Update README and docstrings
