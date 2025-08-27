from pydantic import BaseModel, Field
from typing import Optional, Dict
from src.specs.common.ids import EntityIds

class OrchestrateContentRequest(EntityIds):
    payload: Dict = Field(default_factory=dict)  # { "postPlanId": "...", ... } if you send more

class OrchestrateContentResponse(BaseModel):
    accepted: bool
    runTraceId: str
    next: str = "/api/check_task_status?runTraceId={runTraceId}"

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    errorCode: Optional[str] = None
    details: Optional[Dict] = None
