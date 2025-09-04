from __future__ import annotations

import importlib
import json
import logging
import pkgutil
from functools import lru_cache
from typing import Callable, Dict, List, Optional, Tuple

from src.specs.tools_registry import ToolDef
from src.specs.models.tools import ErrorInfo


@lru_cache(maxsize=1)
def _discover() -> Tuple[List[ToolDef], Dict[str, Callable[[dict, Optional[logging.Logger]], object]]]:
    """Discover tool modules in src.tools package.

    Each tool module should export:
      - TOOL_DEF: ToolDef
      - execute(args: dict, logger: Optional[Logger]) -> pydantic BaseModel
    """
    tool_defs: List[ToolDef] = []
    executors: Dict[str, Callable[[dict, Optional[logging.Logger]], object]] = {}

    import src.tools as tools_pkg  # type: ignore

    for modinfo in pkgutil.iter_modules(tools_pkg.__path__):  # type: ignore[arg-type]
        name = modinfo.name
        if not name.endswith("_tool"):
            continue
        if name in {"registry"}:
            continue
        try:
            module = importlib.import_module(f"src.tools.{name}")
        except Exception:
            # Skip modules that fail to import (e.g., missing optional deps)
            continue
        tool_def = getattr(module, "TOOL_DEF", None) or getattr(module, "tool_def", None)
        execute = getattr(module, "execute", None)
        if tool_def and execute:
            tool_defs.append(tool_def)
            executors[tool_def.name] = execute

    return tool_defs, executors


def list_tool_defs() -> List[ToolDef]:
    defs, _ = _discover()
    return list(defs)


def build_function_tools() -> List[dict]:
    """Return agent function tool specs derived from discovered ToolDefs.

    Uses Pydantic model JSON schema as tool parameters. Adjust the key
    from `parameters` to `input_schema` if required by your SDK variant.
    """
    defs, _ = _discover()
    tools: List[dict] = []
    for t in defs:
        try:
            schema = t.input_model.model_json_schema()
        except Exception:
            schema = t.input_model.schema()  # type: ignore[attr-defined]
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": schema,
                },
            }
        )
    return tools


def execute_tool(name: str, args: dict, logger: Optional[logging.Logger] = None) -> str:
    """Execute a tool and return a JSON string envelope for the agent.

    Unknown tools return a standardized error envelope.
    """
    _, executors = _discover()
    handler = executors.get(name)
    if not handler:
        err = ErrorInfo(code="UnknownTool", message=f"Tool '{name}' not implemented")
        return json.dumps({"status": "failed", "result": None, "error": err.model_dump()})
    resp = handler(args, logger)
    try:
        return resp.model_dump_json()  # type: ignore[attr-defined]
    except Exception:
        try:
            return json.dumps(resp.dict())  # type: ignore[attr-defined]
        except Exception:
            # Last resort: wrap raw in a failed envelope
            err = ErrorInfo(code="SerializationError", message="Failed to serialize tool response")
            return json.dumps({"status": "failed", "result": None, "error": err.model_dump()})


__all__ = [
    "list_tool_defs",
    "build_function_tools",
    "execute_tool",
]
