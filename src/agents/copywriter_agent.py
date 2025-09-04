import os
import logging
from functools import lru_cache
from typing import Optional

from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient

from .agent_registry import AgentRegistry
from src.tools.registry import build_function_tools, execute_tool


@lru_cache(maxsize=1)
def _get_client(endpoint: str) -> AgentsClient:
    credential = DefaultAzureCredential()
    return AgentsClient(endpoint, credential)


def ensure_copywriter_agent_id(
    *,
    endpoint: str,
    model_deployment: Optional[str],
    agent_name: str = "AutogenSocialCopywriter",
    logger: Optional[logging.Logger] = None,
) -> Optional[str]:
    """Ensure an agent suitable for copywriting exists and return its ID.

    Resolution order:
      1) Check persisted registry by `agent_name`
      2) Search existing agents by name
      3) Create a new agent (requires `model_deployment`)
    The resolved id is stored in the registry for future use.
    """
    log = logger or logging.getLogger("autogensocial")
    client = _get_client(endpoint)

    # 1) Check registry
    registry = AgentRegistry()
    reg_id = registry.get(agent_name)
    if reg_id:
        try:
            _ = client.get_agent(reg_id)
            try:
                _ensure_agent_tools(client, reg_id, log)
            except Exception:
                pass
            return reg_id
        except Exception:
            pass

    # 2) Search by name
    try:
        for agent in client.list_agents():  # type: ignore[assignment]
            try:
                if getattr(agent, "name", None) == agent_name:
                    registry.set(agent_name, agent.id)  # type: ignore[attr-defined]
                    try:
                        _ensure_agent_tools(client, agent.id, log)  # type: ignore[arg-type]
                    except Exception:
                        pass
                    return agent.id  # type: ignore[attr-defined]
            except Exception:
                continue
    except Exception as exc:  # pragma: no cover - best effort
        log.warning("Failed to list agents: %s", exc)

    # 3) Create new
    if not model_deployment:
        log.warning(
            "MODEL_DEPLOYMENT_NAME not set; cannot create agent '%s'", agent_name
        )
        return None
    try:
        # Create agent with function tools for data access
        tools = build_function_tools()
        created = client.create_agent(
            name=agent_name,
            model=model_deployment,
            instructions=(
                "You are a copywriter agent for AutogenSocial. "
                "Generate concise, engaging social media captions and hashtags. "
                "Use the provided tools (get_brand, get_post_plan) to fetch brand "
                "and plan details before drafting content when helpful."
            ),
            tools=tools,
        )
        agent_id = created.id  # type: ignore[attr-defined]
        registry.set(agent_name, agent_id)
        log.info("Created agent '%s' with id %s", agent_name, agent_id)
        return agent_id
    except Exception as exc:  # pragma: no cover - best effort
        log.exception("Failed to create agent '%s': %s", agent_name, exc)
        return None


def generate_content_ref(
    brand_id: str,
    post_plan_id: str,
    *,
    endpoint: Optional[str] = None,
    agent_id: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> str:
    """
    Generate a content reference by invoking the Azure AI Foundry copywriter agent.

    Falls back to a deterministic draft reference if configuration is missing
    or the agent invocation fails.
    """
    log = logger or logging.getLogger("autogensocial")

    endpoint = endpoint or os.getenv("PROJECT_ENDPOINT")

    if not endpoint:
        log.warning("PROJECT_ENDPOINT not set; returning placeholder contentRef")
        return f"draft:{brand_id}:{post_plan_id}"

    # If no agent_id is supplied, resolve via registry or create one
    if not agent_id:
        ensured = ensure_copywriter_agent_id(
            endpoint=endpoint,
            model_deployment=os.getenv("MODEL_DEPLOYMENT_NAME"),
            agent_name=os.getenv("COPYWRITER_AGENT_NAME", "AutogenSocialCopywriter"),
            logger=log,
        )
        if ensured:
            agent_id = ensured
        else:
            log.warning("No agent available; returning placeholder contentRef")
            return f"draft:{brand_id}:{post_plan_id}"

    try:
        client = _get_client(endpoint)
        instructions = (
            f"Write social media copy for brand {brand_id} and plan {post_plan_id}."
        )
        run = client.create_thread_and_run(
            agent_id=agent_id,
            instructions=instructions,
        )
        # Process tool calls until run completes or fails; return run id as contentRef
        try:
            _process_run_until_complete(client, run)
        except Exception:
            # Best-effort; even if tooling fails we still return the run id
            pass
        return run.id
    except Exception as exc:  # pragma: no cover - best effort
        log.exception("Failed to invoke copywriter agent: %s", exc)
        return f"draft:{brand_id}:{post_plan_id}"


# ---- Function tools integration ----

def _build_function_tools():
    # Backwards compatibility: delegate to centralized registry
    return build_function_tools()


def _ensure_agent_tools(client: AgentsClient, agent_id: str, logger: Optional[logging.Logger] = None) -> None:
    """Best-effort ensure that the agent has our function tools attached.

    If the SDK exposes an update method, try to set tools; otherwise, no-op.
    """
    log = logger or logging.getLogger("autogensocial")
    tools = _build_function_tools()
    try:
        # Some SDKs expose update_agent(agent_id=..., tools=[...])
        client.update_agent(agent_id=agent_id, tools=tools)  # type: ignore[attr-defined]
        log.info("Updated agent %s with %d tools", agent_id, len(tools))
    except Exception as exc:
        # If update is not supported, log at debug to avoid noise
        log.debug("Could not update agent tools for %s: %s", agent_id, exc)


def _process_run_until_complete(client: AgentsClient, run) -> None:
    """Poll the run; if tools are requested, execute and submit outputs.

    Compatible with Agents API patterns where a run reports `status`
    and may include `required_action.submit_tool_outputs.tool_calls`.
    """
    import json
    import time

    # Attempt to extract thread id from the run; fallback to attribute
    thread_id = getattr(run, "thread_id", None)
    run_id = getattr(run, "id", None)
    if not (thread_id and run_id):
        return

    while True:
        current = client.get_run(thread_id=thread_id, run_id=run_id)
        status = getattr(current, "status", None)
        # When tools are needed, the run indicates a required action
        required_action = getattr(current, "required_action", None)
        if required_action and getattr(required_action, "type", None) == "submit_tool_outputs":
            tool_calls = getattr(required_action, "submit_tool_outputs", None)
            tool_calls = getattr(tool_calls, "tool_calls", []) if tool_calls else []
            outputs = []
            for call in tool_calls:
                call_id = getattr(call, "id", None)
                name = getattr(call, "name", None)
                arguments = getattr(call, "arguments", "{}")
                try:
                    args = json.loads(arguments) if isinstance(arguments, str) else arguments
                except Exception:
                    args = {}
                # Dispatch to local tool functions
                output_text = _execute_tool(name, args)
                outputs.append({"tool_call_id": call_id, "output": output_text})
            if outputs:
                client.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run_id,
                    tool_outputs=outputs,
                )
            # Loop will continue and poll again
        elif status in {"completed", "failed", "cancelled", "expired"}:
            return
        time.sleep(0.75)


def _execute_tool(name: str, args: dict) -> str:
    """Delegate to centralized tools registry for execution."""
    return execute_tool(name, args)
