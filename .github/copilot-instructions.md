## Copilot Instructions for Azure Functions with AI Foundry Multi-Agent Workflow (Python)

### 1. Python Naming Conventions (PEP 8)
- Modules & files: `lowercase_with_underscores`
- Packages & folders: `lowercase_with_underscores`
- Classes: `CapitalizedWords` (PascalCase)
- Functions & methods: `lowercase_with_underscores`
- Variables: `lowercase_with_underscores`
- Constants: `ALL_UPPERCASE_WITH_UNDERSCORES`
- Private members: `_single_leading_underscore`
- Magic methods: `__double_leading_and_trailing_underscores__`

### 2. Azure Functions Best Practices
- Use the `azure-functions` Python library for function definitions.
- Each function should have a clear entrypoint (e.g., `main(req: func.HttpRequest) -> func.HttpResponse`).
- Use dependency injection for services (e.g., CosmosDB clients, AI agents).
- Store configuration in environment variables or `local.settings.json`.
- Log using the provided logger or `logging` module.
- Handle errors gracefully and return meaningful HTTP responses.

### 3. AI Foundry Multi-Agent Workflow
- Use Azure Foundry AI Agents and Azure AI Function Tools for orchestration.
- Define each agent as a class following PEP 8 naming.
- Use async/await for agent orchestration if supported.
- Pass context and state between agents using structured objects or dictionaries.
- Log agent actions and decisions for traceability.

### 4. CosmosDB Integration
- Use the `azure-cosmos` Python SDK.
- Store and retrieve agent state, workflow results, and logs in CosmosDB.
- Use dependency injection for CosmosDB clients.
- Follow best practices for partition keys and throughput.

### 5. Example Structure

```python
# main.py
import azure.functions as func
from agents.workflow_orchestrator import WorkflowOrchestrator
from utils.cosmos_client import get_cosmos_client

def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
	"""Entrypoint for Azure Function running AI Foundry multi-agent workflow."""
	cosmos_client = get_cosmos_client()
	orchestrator = WorkflowOrchestrator(cosmos_client)
	try:
		result = orchestrator.run(req.get_json())
		return func.HttpResponse(result, status_code=200)
	except Exception as exc:
		# Log error and return 500
		context.logger.error(f"Workflow failed: {exc}")
		return func.HttpResponse("Internal Server Error", status_code=500)
```

```python
# agents/workflow_orchestrator.py
class WorkflowOrchestrator:
	def __init__(self, cosmos_client):
		self.cosmos_client = cosmos_client
		# Initialize agents here

	def run(self, input_data: dict) -> dict:
		# Orchestrate multi-agent workflow
		# ...
		return {"status": "success"}
```

### 6. General Guidelines
- Write docstrings for all public classes and functions.
- Use type hints for function signatures.
- Keep functions small and focused.
- Use environment variables for secrets and connection strings.
- Write unit tests for all logic.

---
Follow these instructions to ensure all generated code is production-ready, maintainable, and aligned with Azure and Python best practices.
