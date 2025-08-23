from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class TraceLogEvent(BaseModel):
    runTraceId: str = Field(..., description="Trace/session identifier")
    event: str = Field(..., description="Event name or type")
    timestamp: datetime = Field(..., description="Event timestamp (UTC)")
    level: str = Field("INFO", description="Log level (e.g., INFO, ERROR, DEBUG)")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional event data")
