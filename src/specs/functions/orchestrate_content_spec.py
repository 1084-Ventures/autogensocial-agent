
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal

class OrchestrateContentRequest(BaseModel):
    runTraceId: str = Field(..., description="Unique identifier for tracing/logging")
    brandId: str = Field(..., description="Brand identifier")
    # Add other relevant fields as needed
    # e.g. userId: Optional[str], postPlanId: Optional[str], etc.
    payload: Optional[Dict[str, Any]] = Field(None, description="Additional request payload")

class OrchestrateContentResponse(BaseModel):
    success: bool = Field(..., description="Indicates if orchestration was successful")
    message: Optional[str] = Field(None, description="Status or error message")
    postId: Optional[str] = Field(None, description="ID of the published post")
    # Add other relevant fields as needed
    data: Optional[Dict[str, Any]] = Field(None, description="Additional response data")

# Error response model (optional, for explicit error typing)
class OrchestrateContentErrorResponse(BaseModel):
    success: Literal[False] = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Any] = None

"""
Spec for orchestrate_content HTTP function.

This function orchestrates the end-to-end process of generating, composing, and publishing social media content.
It coordinates multiple tools, agents, and services, and logs each step using TraceLogger.

Request Model: OrchestrateContentRequest
Response Model: OrchestrateContentResponse (or OrchestrateContentErrorResponse on error)

See diagrams/autogensocial_http_sequence.mmd for orchestration flow.
See individual tool/agent spec files for detailed contracts.
"""
