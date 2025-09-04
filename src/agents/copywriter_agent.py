import os
import logging
import asyncio
from functools import lru_cache
from typing import Optional, Dict
from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient
from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
from azure.ai.agents.aio import AgentsClient as AsyncAgentsClient

from .agent_registry import AgentRegistry
from src.tools.registry import build_function_tools, execute_tool, list_tool_defs


@lru_cache(maxsize=1)
def _get_client(endpoint: str) -> AgentsClient:
    credential = DefaultAzureCredential()
    return AgentsClient(endpoint, credential)


_async_client_cache: Dict[str, AsyncAgentsClient] = {}
_async_credential: Optional[AsyncDefaultAzureCredential] = None


def _get_async_client(endpoint: str) -> AsyncAgentsClient:
    global _async_credential
    if endpoint in _async_client_cache:
        return _async_client_cache[endpoint]
    if _async_credential is None:
        _async_credential = AsyncDefaultAzureCredential()
    client = AsyncAgentsClient(endpoint, _async_credential)
    _async_client_cache[endpoint] = client
    return client


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
                _ensure_agent_config(client, reg_id, agent_name, registry, log)
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
                        _ensure_agent_config(client, agent.id, agent_name, registry, log)  # type: ignore[arg-type]
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
        desired_instructions = _resolve_desired_instructions(agent_name, registry, log)
        created = client.create_agent(
            name=agent_name,
            model=model_deployment,
            instructions=desired_instructions,
            tools=tools,
        )
        agent_id = created.id  # type: ignore[attr-defined]
        registry.set(agent_name, agent_id)
        _persist_agent_config_snapshot(agent_name, agent_id, registry, log)
        log.info("Created agent '%s' with id %s", agent_name, agent_id)
        return agent_id
    except Exception as exc:  # pragma: no cover - best effort
        log.exception("Failed to create agent '%s': %s", agent_name, exc)
        return None


async def generate_content_ref(
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
        client = _get_async_client(endpoint)
        instructions = (
            f"Write social media copy for brand {brand_id} and plan {post_plan_id}."
        )
        run = await client.create_thread_and_run(
            agent_id=agent_id,
            instructions=instructions,
        )
        try:
            await _process_run_until_complete(client, run)
        except Exception:
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


def _resolve_desired_instructions(
    agent_name: str, registry: AgentRegistry, logger: Optional[logging.Logger] = None
) -> str:
    """Determine instructions from Cosmos config or seed from local file.

    - If config doc has 'instructions', use it.
    - Else, load from 'src/agents/instructions/{slug}.md'; persist to config for future.
    - Else, fall back to code default.
    """
    log = logger or logging.getLogger("autogensocial")
    cfg = registry.get_config(agent_name) or {}
    instr = (cfg or {}).get("instructions") if isinstance(cfg, dict) else None
    if isinstance(instr, str) and instr.strip():
        return instr
    # Try file seed
    slug = _slugify(agent_name)
    here = Path(__file__).resolve().parent
    fpath = here / "instructions" / f"{slug}.md"
    if fpath.exists():
        try:
            text = fpath.read_text(encoding="utf-8").strip()
            if text:
                # Persist
                cfg = cfg if isinstance(cfg, dict) else {}
                cfg.update({
                    "logicalName": agent_name,
                    "instructions": text,
                    "tools": [t.name for t in list_tool_defs()],
                })
                registry.upsert_config(agent_name, cfg)
                return text
        except Exception as exc:
            log.debug("Failed to read default instructions file %s: %s", fpath, exc)
    # Code fallback
    return (
        "You are a copywriter agent for AutogenSocial. "
        "Generate concise, engaging social media captions and hashtags. "
        "Use the provided tools to fetch brand and plan details before drafting content."
    )


def _persist_agent_config_snapshot(
    agent_name: str, agent_id: str, registry: AgentRegistry, logger: Optional[logging.Logger] = None
) -> None:
    log = logger or logging.getLogger("autogensocial")
    cfg = registry.get_config(agent_name) or {}
    if not isinstance(cfg, dict):
        cfg = {}
    cfg.update({"logicalName": agent_name, "agentId": agent_id})
    try:
        registry.upsert_config(agent_name, cfg)
    except Exception as exc:
        log.debug("Failed to persist agent config snapshot: %s", exc)


def _ensure_agent_config(
    client: AgentsClient,
    agent_id: str,
    agent_name: str,
    registry: AgentRegistry,
    logger: Optional[logging.Logger] = None,
) -> None:
    """Ensure the remote agent's instructions match the desired config."""
    log = logger or logging.getLogger("autogensocial")
    desired = _resolve_desired_instructions(agent_name, registry, log)
    try:
        details = client.get_agent(agent_id)
        current = getattr(details, "instructions", None)
        if isinstance(current, str) and current.strip() == desired.strip():
            return
    except Exception:
        # If we can't read details, attempt update anyway
        pass
    try:
        client.update_agent(agent_id=agent_id, instructions=desired)  # type: ignore[attr-defined]
        _persist_agent_config_snapshot(agent_name, agent_id, registry, log)
        log.info("Updated agent %s instructions from config", agent_id)
    except Exception as exc:
        log.debug("Could not update agent instructions for %s: %s", agent_id, exc)


def _slugify(name: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")


async def _process_run_until_complete(client: AsyncAgentsClient, run) -> None:
    """Asynchronously poll the run and handle tool call submissions."""
    import json

    thread_id = getattr(run, "thread_id", None)
    run_id = getattr(run, "id", None)
    if not (thread_id and run_id):
        return

    while True:
        current = await client.get_run(thread_id=thread_id, run_id=run_id)
        status = getattr(current, "status", None)
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
                output_text = await asyncio.to_thread(_execute_tool, name, args)
                outputs.append({"tool_call_id": call_id, "output": output_text})
            if outputs:
                await client.submit_tool_outputs(
                    thread_id=thread_id,
                    run_id=run_id,
                    tool_outputs=outputs,
                )
        elif status in {"completed", "failed", "cancelled", "expired"}:
            return
        await asyncio.sleep(0.75)


def _execute_tool(name: str, args: dict) -> str:
    """Delegate to centralized tools registry for execution."""
    return execute_tool(name, args)
