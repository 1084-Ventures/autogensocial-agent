"""
Specification for the trace logging functionality.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Protocol
from datetime import datetime

class TraceLogEvent(BaseModel):
    """
    Model representing a trace log event.
    """
    runTraceId: str = Field(..., description="Trace/session identifier")
    event: str = Field(..., description="Event name or type")
    timestamp: datetime = Field(..., description="Event timestamp (UTC)")
    level: str = Field("INFO", description="Log level (e.g., INFO, ERROR, DEBUG)")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional event data")

class TraceLogger(Protocol):
    """
    Protocol defining the interface for trace logging functionality.
    """
    async def log_event(
        self,
        run_trace_id: str,
        event: str,
        level: str = "INFO",
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a trace event.
        
        Args:
            run_trace_id: Unique identifier for the trace/session
            event: Event name or description
            level: Log level (INFO, ERROR, DEBUG)
            data: Optional additional event data
        """
        ...
