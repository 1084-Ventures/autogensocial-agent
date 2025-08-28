import json
import os
import time
from typing import Any, Dict, List, Optional

try:
    from azure.ai.projects import AIProjectClient  # type: ignore
    from azure.identity import DefaultAzureCredential  # type: ignore
except Exception:  # pragma: no cover
    AIProjectClient = None  # type: ignore
    DefaultAzureCredential = None  # type: ignore

from src.specs.agents.image import ImageAgentInput, ImageAgentOutput
from src.shared.state import RunStateStore
from src.tools.get_brand_tool import FUNCTION_TOOL as BRAND_TOOL, call_function_tool as call_brand
from src.tools.get_post_plan_tool import FUNCTION_TOOL as PLAN_TOOL, call_function_tool as call_plan
from src.tools.search_images_tool import FUNCTION_TOOL as SEARCH_TOOL, call_function_tool as call_search
from src.tools.image_creation_tools import FUNCTION_TOOLS as IMG_TOOLS, call_function_tool as call_img_tool
from src.shared.retry_utils import retry_with_backoff
from .base import Agent


class FoundryImageAgent(Agent):
    """Agent that selects the best image for a post.

    - Can search the web for candidate images
    - Can persist a chosen web image
    - Can generate a new image (Azure OpenAI if configured), and persist it
    - Uses brand and post plan info via tools
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
            "You are the ImageComposerAgent for AutogenSocial. "
            "Task: pick the best image for this post given brand and plan. "
            "Steps: 1) Search the web first (search_images) with brand/topic keywords. "
            "Evaluate candidates for brand-safety and license suitability (prefer ShareCommercially/Public). "
            "If a suitable image is found, persist it using persist_image_from_url and include source metadata "
            "(license, title, hostPage, provider, width, height, thumbnail). "
            "If none are suitable, craft a concise prompt (<=60 tokens) and call generate_image_from_prompt. "
            "Return only the final {\"mediaRef\": ..., \"url\": ...}."
        )

    def _create_agent(self):
        tools = [BRAND_TOOL, PLAN_TOOL, SEARCH_TOOL, IMG_TOOLS["persist_image_from_url"], IMG_TOOLS["generate_image_from_prompt"]]
        return self._client.agents.create_agent(
            model=self.model,
            name="image-composer-agent",
            instructions=self._build_instructions(),
            tools=tools,
        )

    def _ensure_thread(self):
        return self._client.agents.threads.create()

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
        # Create run with retry
        run = retry_with_backoff(
            lambda: self._client.agents.runs.create(thread_id=thread_id, agent_id=agent_id),
            attempts=3,
        )
        # Poll with tolerance for transient GET errors
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
                                RunStateStore.add_event(self._run_trace_id, phase="image", action="tool:get_brand", data={"args": args})  # type: ignore[attr-defined]
                        except Exception:
                            pass
                    elif name == PLAN_TOOL["function"]["name"]:
                        result = call_plan(args)
                        try:
                            if getattr(self, "_run_trace_id", None):
                                RunStateStore.add_event(self._run_trace_id, phase="image", action="tool:get_post_plan", data={"args": args})  # type: ignore[attr-defined]
                        except Exception:
                            pass
                    elif name == SEARCH_TOOL["function"]["name"]:
                        result = call_search(args)
                        try:
                            if getattr(self, "_run_trace_id", None):
                                cnt = len(((result or {}).get("result") or {}).get("items") or [])
                                RunStateStore.add_event(self._run_trace_id, phase="image", action="tool:search_images", data={"query": args.get("query"), "count": cnt})  # type: ignore[attr-defined]
                        except Exception:
                            pass
                    elif name == IMG_TOOLS["persist_image_from_url"]["function"]["name"]:
                        result = call_img_tool(name, args)
                        try:
                            if getattr(self, "_run_trace_id", None):
                                RunStateStore.add_event(self._run_trace_id, phase="image", action="tool:persist_image_from_url", data={"url": args.get("url")})  # type: ignore[attr-defined]
                        except Exception:
                            pass
                    elif name == IMG_TOOLS["generate_image_from_prompt"]["function"]["name"]:
                        result = call_img_tool(name, args)
                        try:
                            if getattr(self, "_run_trace_id", None):
                                RunStateStore.add_event(self._run_trace_id, phase="image", action="tool:generate_image_from_prompt", data={"hasPrompt": bool(args.get("prompt"))})  # type: ignore[attr-defined]
                        except Exception:
                            pass
                    else:
                        result = {"status": "failed", "error": {"code": "unknown_tool", "message": f"{name}"}}
                    outputs.append({"tool_call_id": getattr(tc, "id", None), "output": json.dumps(result)})
                run = self._submit_tool_outputs_with_retry(thread_id=thread_id, run_id=run.id, outputs=outputs)
                continue
            time.sleep(0.75)
        msgs = list(self._client.agents.messages.list(thread_id=thread_id))
        assistant_msgs = [m for m in msgs if getattr(m, "role", None) == "assistant"]
        final_msg = assistant_msgs[-1] if assistant_msgs else (msgs[-1] if msgs else None)
        text = self._content_to_text(getattr(final_msg, "content", "")) if final_msg else ""
        return {"role": getattr(final_msg, "role", None) if final_msg else None, "content": text}

    def run(self, ipt: ImageAgentInput) -> ImageAgentOutput:
        with self._client:
            agent = self._create_agent()
            try:
                # stash run id for event logging
                self._run_trace_id = ipt.runTraceId
                thread = self._ensure_thread()
                # System prompt expects tool calls; provide context
                self._client.agents.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=(
                        "Select the best image for this post.\n"
                        f"brandId: {ipt.brandId}\npostPlanId: {ipt.postPlanId}\nrunTraceId: {ipt.runTraceId}\n"
                        f"caption: {ipt.caption or ''}\n"
                        "- If a good web image exists, call search_images then persist_image_from_url.\n"
                        "- If not, call generate_image_from_prompt with a concise prompt (<=60 tokens).\n"
                        "Return only the final image reference and url."
                    ),
                )
                final = self._process_run(thread_id=thread.id, agent_id=agent.id)
                # The assistant may return JSON or text; try to parse mediaRef and url
                content = (final.get("content") or "").strip()
                media_ref: Optional[str] = None
                url: Optional[str] = None
                try:
                    obj = json.loads(content)
                    media_ref = obj.get("mediaRef") or (obj.get("result") or {}).get("mediaRef")
                    url = obj.get("url") or (obj.get("result") or {}).get("url")
                except Exception:
                    # naive extraction
                    for line in content.splitlines():
                        if line.lower().startswith("mediaref") and ":" in line:
                            media_ref = line.split(":", 1)[1].strip().strip('"')
                        if line.lower().startswith("url") and ":" in line:
                            url = line.split(":", 1)[1].strip().strip('"')
                if not (media_ref and url):
                    # As a safeguard, generate placeholder
                    fallback = call_img_tool(
                        "generate_image_from_prompt",
                        {"brandId": ipt.brandId, "postPlanId": ipt.postPlanId, "runTraceId": ipt.runTraceId, "prompt": ipt.caption or ""},
                    )
                    res = (fallback.get("result") or {})
                    media_ref = res.get("mediaRef")
                    url = res.get("url")
                return ImageAgentOutput(mediaRef=media_ref or "", url=url or "", provider=None, extras={})
            finally:
                try:
                    self._client.agents.delete_agent(agent.id)
                except Exception:
                    pass
