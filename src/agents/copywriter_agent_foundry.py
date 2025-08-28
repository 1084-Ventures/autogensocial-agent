import json
import os
import uuid
import time
from typing import Any, Dict, List, Optional

try:
    from azure.ai.projects import AIProjectClient  # type: ignore
    from azure.identity import DefaultAzureCredential  # type: ignore
except Exception:  # pragma: no cover
    AIProjectClient = None  # type: ignore
    DefaultAzureCredential = None  # type: ignore

try:
    from azure.cosmos import CosmosClient  # type: ignore
except Exception:  # pragma: no cover
    CosmosClient = None  # type: ignore

from src.specs.agents.copywriter import CopywriterInput, CopywriterOutput
from src.shared.state import RunStateStore
from src.tools.get_brand_tool import FUNCTION_TOOL as BRAND_TOOL, call_function_tool as call_brand
from src.tools.get_post_plan_tool import FUNCTION_TOOL as PLAN_TOOL, call_function_tool as call_plan
from src.shared.logging_utils import info as log_info
from src.shared.retry_utils import retry_with_backoff
from .base import Agent


class FoundryCopywriterAgent(Agent):
    """Copywriter agent using Azure AI Foundry Agents SDK (AIProjectClient).

    Registers function tools (get_brand, get_post_plan), runs the agent, handles
    requires_action by executing tools, returns final caption and hashtags, and
    persists the draft to Cosmos when configured.
    """

    def __init__(self, *, model: Optional[str] = None) -> None:
        super().__init__()
        if AIProjectClient is None or DefaultAzureCredential is None:
            raise RuntimeError(
                "Azure AI Foundry Agents SDK not available. Install 'azure-ai-projects' and 'azure-identity'."
            )
        endpoint = os.getenv("PROJECT_ENDPOINT")
        if not endpoint:
            raise RuntimeError("PROJECT_ENDPOINT is required for AIProjectClient")
        self.model = model or os.getenv("MODEL_DEPLOYMENT_NAME")
        if not self.model:
            raise RuntimeError("MODEL_DEPLOYMENT_NAME is required for AI agent model")
        disable_mi = (os.getenv("AZURE_IDENTITY_DISABLE_MANAGED_IDENTITY", "").lower() in ("1", "true", "yes"))
        cred = DefaultAzureCredential(exclude_managed_identity_credential=disable_mi)
        self._client = AIProjectClient(endpoint=endpoint, credential=cred)

    def _build_instructions(self) -> str:
        return (
            "You are CopywriterAgent for AutogenSocial. "
            "Plan, reason, and draft concise social captions that align to the brand's voice and the post plan brief. "
            "Use the available tools to fetch brand and post plan context before writing. "
            "Return a single best caption and a brief list of relevant hashtags."
        )

    def _create_agent(self):
        tools = [BRAND_TOOL, PLAN_TOOL]
        return self._client.agents.create_agent(
            model=self.model,
            name="copywriter-agent",
            instructions=self._build_instructions(),
            tools=tools,
        )

    def _ensure_thread(self):
        return self._client.agents.threads.create()

    def _persist_content(self, *, brand_id: str, post_plan_id: str, caption: str, hashtags: List[str]) -> str:
        conn = os.getenv("COSMOS_DB_CONNECTION_STRING")
        db_name = os.getenv("COSMOS_DB_NAME")
        container_name = os.getenv("COSMOS_DB_CONTAINER_POSTS")
        if not conn or not db_name or not container_name or CosmosClient is None:
            return f"content/{uuid.uuid4().hex}.json"
        client = CosmosClient.from_connection_string(conn)
        db = client.get_database_client(db_name)
        container = db.get_container_client(container_name)
        doc_id = f"content-{uuid.uuid4().hex}"
        body = {
            "id": doc_id,
            "partitionKey": brand_id,
            "brandId": brand_id,
            "postPlanId": post_plan_id,
            "type": "generatedContent",
            "status": "draft",
            "content": {"caption": caption, "hashtags": hashtags},
        }
        try:
            container.upsert_item(body)
            log_info(
                getattr(self, "_run_trace_id", None),
                "cosmos:posts:upsert_content",
                docId=doc_id,
                brandId=brand_id,
                postPlanId=post_plan_id,
                captionLen=len(caption),
                hashtags=len(hashtags),
            )
        except Exception as exc:
            log_info(
                getattr(self, "_run_trace_id", None),
                "cosmos:posts:upsert_failed",
                docId=doc_id,
                error=str(exc),
            )
        return doc_id

    @staticmethod
    def _parse_output_text(text: str) -> (str, List[str]):
        caption = text.strip()
        hashtags: List[str] = []
        if "\n#" in caption or caption.startswith("#"):
            lines = [ln.strip() for ln in caption.splitlines() if ln.strip()]
            if lines:
                caption = lines[0]
                tag_text = " ".join(lines[1:])
                hashtags = [t for t in tag_text.split() if t.startswith("#")]
        return caption, hashtags

    def _content_to_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            chunks: List[str] = []
            for part in content:
                if isinstance(part, dict):
                    val = part.get("text") or part.get("content") or part.get("value")
                    if isinstance(val, str):
                        chunks.append(val)
            return "\n".join(chunks)
        return ""

    def _submit_tool_outputs_with_retry(self, *, thread_id: str, run_id: str, outputs: List[Dict[str, Any]]):
        return retry_with_backoff(
            lambda: self._client.agents.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run_id,
                tool_outputs=outputs,
            ),
            attempts=4,
        )

    def _process_run(self, *, thread_id: str, agent_id: str) -> Dict[str, Any]:
        # Create run with simple backoff in case of transient disconnects
        run = retry_with_backoff(
            lambda: self._client.agents.runs.create(thread_id=thread_id, agent_id=agent_id),
            attempts=3,
        )
        # Poll the run, tolerating occasional GET failures
        backoff = 0.75
        while True:
            try:
                run = self._client.agents.runs.get(thread_id=thread_id, run_id=run.id)
            except Exception:
                time.sleep(min(backoff * 2, 3.0))
                backoff = min(backoff * 1.5, 3.0)
                continue
            status = (getattr(run, "status", None) or "").lower()
            if status in {"succeeded", "completed"}:
                break
            if status in {"failed", "cancelled", "canceled"}:
                raise RuntimeError(f"Agent run {status}: {getattr(run, 'last_error', None)}")
            if status == "requires_action":
                required = getattr(run, "required_action", None) or {}
                submit = getattr(required, "submit_tool_outputs", None) or {}
                tool_calls = getattr(submit, "tool_calls", None) or []
                outputs = []
                for tc in tool_calls:
                    name = getattr(getattr(tc, "function", None), "name", None)
                    args_str = getattr(getattr(tc, "function", None), "arguments", "{}") or "{}"
                    try:
                        args = json.loads(args_str)
                    except Exception:
                        args = {}
                    if name == BRAND_TOOL["function"]["name"]:
                        result = call_brand(args)
                        try:
                            if getattr(self, "_run_trace_id", None):
                                RunStateStore.add_event(self._run_trace_id, phase="copywriter", action="tool:get_brand", data={"args": args})  # type: ignore[attr-defined]
                        except Exception:
                            pass
                    elif name == PLAN_TOOL["function"]["name"]:
                        result = call_plan(args)
                        try:
                            if getattr(self, "_run_trace_id", None):
                                RunStateStore.add_event(self._run_trace_id, phase="copywriter", action="tool:get_post_plan", data={"args": args})  # type: ignore[attr-defined]
                        except Exception:
                            pass
                    else:
                        result = {"status": "failed", "error": {"code": "unknown_tool", "message": f"{name}"}}
                    outputs.append({"tool_call_id": getattr(tc, "id", None), "output": json.dumps(result)})
                run = self._submit_tool_outputs_with_retry(thread_id=thread_id, run_id=run.id, outputs=outputs)
                continue
            # queued or in_progress
            time.sleep(0.75)
        # On completion, get messages and return last assistant content as text
        try:
            msgs = list(self._client.agents.messages.list(thread_id=thread_id))
        except Exception:
            msgs = []
        assistant_msgs = [m for m in msgs if getattr(m, "role", None) == "assistant"]
        final_msg = assistant_msgs[-1] if assistant_msgs else (msgs[-1] if msgs else None)
        text = self._content_to_text(getattr(final_msg, "content", "")) if final_msg else ""
        return {"role": getattr(final_msg, "role", None) if final_msg else None, "content": text}

    def run(self, ipt: CopywriterInput) -> CopywriterOutput:
        with self._client:
            agent = self._create_agent()
            try:
                self._run_trace_id = getattr(ipt, "runTraceId", None)
                thread = self._ensure_thread()
                self._client.agents.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=(
                        "Create an on-brand social caption for the current plan.\n"
                        f"brandId: {ipt.brandId}\npostPlanId: {ipt.postPlanId}\n"
                        "Use the tools to fetch context as needed, then produce the final caption and hashtags."
                    ),
                )
                final = self._process_run(thread_id=thread.id, agent_id=agent.id)
                text = (final.get("content") or "").strip()
                caption, hashtags = self._parse_output_text(text)
                content_ref = self._persist_content(
                    brand_id=ipt.brandId, post_plan_id=ipt.postPlanId, caption=caption, hashtags=hashtags
                )
                return CopywriterOutput(contentRef=content_ref, caption=caption, hashtags=hashtags, extras={})
            finally:
                try:
                    self._client.agents.delete_agent(agent.id)
                except Exception:
                    pass
