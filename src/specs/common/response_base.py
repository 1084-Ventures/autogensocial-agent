from pydantic import BaseModel, Field
from typing import Optional

class ResponseBase(BaseModel):
    success: bool = Field(..., description="Indicates if the operation was successful")
    message: Optional[str] = Field(None, description="Status or error message")
    traceId: Optional[str] = Field(None, description="Trace/session identifier")
