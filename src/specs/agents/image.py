from pydantic import BaseModel, Field
from typing import Optional, Dict


class ImageAgentInput(BaseModel):
    brandId: str
    postPlanId: str
    runTraceId: str
    caption: Optional[str] = None


class ImageAgentOutput(BaseModel):
    mediaRef: str
    url: str
    provider: Optional[str] = None
    extras: Dict = Field(default_factory=dict)

