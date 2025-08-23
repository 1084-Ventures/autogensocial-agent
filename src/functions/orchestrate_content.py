import azure.functions as func
from src.specs.functions.orchestrate_content_spec import OrchestrateContentRequest, OrchestrateContentResponse, OrchestrateContentErrorResponse
from src.tools.get_brand_tool import get_brand_tool
from src.tools.get_post_plan_tool import get_post_plan_tool
from src.specs.common.trace_logger_spec import TraceLogEvent

app = func.FunctionApp()
import json
import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from datetime import datetime

def log_event(run_trace_id: str, event: str, level: str = "INFO", data: dict = None):
    """Log an event using TraceLogEvent model."""
    trace_event = TraceLogEvent(
        runTraceId=run_trace_id,
        event=event,
        timestamp=datetime.utcnow(),
        level=level,
        data=data
    )
    # For now, just print the event. In production, this would be stored in a logging system
    print(f"[{trace_event.level}] {trace_event.event} - Trace ID: {trace_event.runTraceId}")


def update_post_status(post_id, status):
    # Stub for Cosmos DB update
    print(f"[CosmosDB] Update post {post_id} status to {status}")


# Call the Copywriter Agent as an Azure AI Foundry agent
def call_copywriter_agent(brand_document, post_plan_document, run_trace_id):
    project_endpoint = os.environ.get("PROJECT_ENDPOINT")
    model_name = os.environ.get("MODEL_DEPLOYMENT_NAME")
    if not project_endpoint or not model_name:
        raise EnvironmentError("PROJECT_ENDPOINT and MODEL_DEPLOYMENT_NAME environment variables must be set.")

    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
    )
    with project_client:
        agent = None
        # Find or create the copywriter agent (in production, you may want to cache this)
        agents = list(project_client.agents.list())
        for a in agents:
            if a.name == "copywriter-agent":
                agent = a
                break
        if not agent:
            raise RuntimeError("copywriter-agent not found. Please deploy the agent first.")

        thread = project_client.agents.threads.create()
        # Compose the request as expected by the agent tool
        tool_input = {
            "brand_document": brand_document,
            "post_plan_document": post_plan_document,
            "run_trace_id": run_trace_id
        }
        # Send the message (tool input as content)
        message = project_client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=json.dumps(tool_input),
        )
        run = project_client.agents.runs.create_and_process(
            thread_id=thread.id,
            agent_id=agent.id,
            additional_instructions="Please address the user as Alex Smith. The user is a marketing manager.",
        )
        if run.status == "failed":
            raise RuntimeError(f"Copywriter agent run failed: {run.last_error}")
        # Get the last message from the agent
        messages = list(project_client.agents.messages.list(thread_id=thread.id))
        for m in reversed(messages):
            if m.role == "assistant":
                try:
                    return json.loads(m.content)
                except Exception:
                    return {"success": False, "message": "Invalid response from copywriter agent."}
        return {"success": False, "message": "No response from copywriter agent."}

@app.function_name(name="orchestrate_content")
@app.route(route="orchestrate_content", auth_level=func.AuthLevel.FUNCTION)
def orchestrate_content(req: func.HttpRequest) -> func.HttpResponse:
    try:
        req_body = req.get_json()
        request = OrchestrateContentRequest(**req_body)
    except Exception as e:
        return func.HttpResponse(
            OrchestrateContentErrorResponse(message=f"Invalid request: {str(e)}").model_dump_json(),
            status_code=400,
            mimetype="application/json"
        )

    run_trace_id = request.runTraceId
    log_event(run_trace_id, "Received OrchestrateContentRequest")

    # Step 1: Get Brand Document
    try:
        brand_document = get_brand_tool(request.brandId)
        log_event(run_trace_id, "Fetched brandDocument")
    except Exception as e:
        return func.HttpResponse(
            OrchestrateContentErrorResponse(message=f"Failed to fetch brand: {str(e)}").model_dump_json(),
            status_code=404,
            mimetype="application/json"
        )

    # Step 2: Get Post Plan Document
    post_plan_id = request.payload.get("postPlanId") if request.payload else None
    if not post_plan_id:
        return func.HttpResponse(
            OrchestrateContentErrorResponse(message="Missing postPlanId in payload").model_dump_json(),
            status_code=400,
            mimetype="application/json"
        )
    try:
        post_plan_document = get_post_plan_tool(post_plan_id)
        log_event(run_trace_id, "Fetched postPlanDocument")
    except Exception as e:
        return func.HttpResponse(
            OrchestrateContentErrorResponse(message=f"Failed to fetch post plan: {str(e)}").model_dump_json(),
            status_code=404,
            mimetype="application/json"
        )

    # Step 3: Update post status (stub)
    update_post_status(post_plan_id, "retrieved brand & plan")
    log_event(run_trace_id, "Updated post: retrieved brand & plan")

    # Step 4: Call Copywriter Agent (stub)
    copywriter_response = call_copywriter_agent(brand_document, post_plan_document, run_trace_id)
    log_event(run_trace_id, "Received CopywriterAgentResponse")

    # Step 5: Update post status (stub)
    update_post_status(post_plan_id, "copywriter complete")
    log_event(run_trace_id, "Updated post: copywriter complete")

    # Step 6: Return OrchestrateContentResponse
    response = OrchestrateContentResponse(
        success=True,
        message="Content orchestration complete",
        postId=post_plan_id,
        data={"copywriter_response": copywriter_response}
    )
    return func.HttpResponse(
        response.model_dump_json(),
        status_code=200,
        mimetype="application/json"
    )
