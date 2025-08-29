import os
import logging
from functools import lru_cache
from typing import Optional

from azure.identity import DefaultAzureCredential
from azure.ai.agents import AgentsClient

from .agent_registry import AgentRegistry


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
      1) Validate `COPYWRITER_AGENT_ID` if set
      2) Check persisted registry by `agent_name`
      3) Search existing agents by name
      4) Create a new agent (requires `model_deployment`)
    The resolved id is stored in the registry for future use.
    """
    log = logger or logging.getLogger("autogensocial")
    client = _get_client(endpoint)

    # 1) Validate env var
    env_agent_id = os.getenv("COPYWRITER_AGENT_ID")
    if env_agent_id:
        try:
            _ = client.get_agent(env_agent_id)
            return env_agent_id
        except Exception as exc:  # pragma: no cover - best effort
            log.warning("Env COPYWRITER_AGENT_ID invalid: %s", exc)

    # 2) Check registry
    registry = AgentRegistry()
    reg_id = registry.get(agent_name)
    if reg_id:
        try:
            _ = client.get_agent(reg_id)
            return reg_id
        except Exception:
            pass

    # 3) Search by name
    try:
        for agent in client.list_agents():  # type: ignore[assignment]
            try:
                if getattr(agent, "name", None) == agent_name:
                    registry.set(agent_name, agent.id)  # type: ignore[attr-defined]
                    return agent.id  # type: ignore[attr-defined]
            except Exception:
                continue
    except Exception as exc:  # pragma: no cover - best effort
        log.warning("Failed to list agents: %s", exc)

    # 4) Create new
    if not model_deployment:
        log.warning(
            "MODEL_DEPLOYMENT_NAME not set; cannot create agent '%s'", agent_name
        )
        return None
    try:
        # Minimal agent creation without tools for now; tools can be added later
        # when the function tools are implemented.
        created = client.create_agent(
            name=agent_name,
            model=model_deployment,
            instructions=(
                "You are a copywriter agent for AutogenSocial. "
                "Generate concise, engaging social media captions and hashtags."
            ),
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
    agent_id = agent_id or os.getenv("COPYWRITER_AGENT_ID")

    if not endpoint:
        log.warning("PROJECT_ENDPOINT not set; returning placeholder contentRef")
        return f"draft:{brand_id}:{post_plan_id}"

    # If no agent_id is supplied/configured, try to ensure one exists
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
        return run.id
    except Exception as exc:  # pragma: no cover - best effort
        log.exception("Failed to invoke copywriter agent: %s", exc)
        return f"draft:{brand_id}:{post_plan_id}"
