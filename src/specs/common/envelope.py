from pydantic import BaseModel, Field
from typing import Any, Optional, Dict, Literal


class ToolResult(BaseModel):
    status: Literal["completed", "failed", "pending"]
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None


