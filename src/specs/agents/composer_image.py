from pydantic import BaseModel, Field
from typing import Optional, Dict

class ComposerImageInput(BaseModel):
    brandId: str
    postPlanId: str
    contentRef: str
    params: Dict = Field(default_factory=dict)       # aspect, style, brand colors, etc.

class ComposerImageOutput(BaseModel):
    mediaRef: str           # blob URL or Cosmos ref
    promptUsed: Optional[str] = None
    variants: Optional[Dict] = None
