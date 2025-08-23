from pydantic import BaseModel, Field
from typing import Optional, Any

class ErrorResponse(BaseModel):
    success: bool = Field(False, const=True)
    message: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Application-specific error code")
    details: Optional[Any] = Field(None, description="Additional error details")
