from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class CopywriterInput(BaseModel):
    brandId: str
    postPlanId: str
    runTraceId: Optional[str] = None

class CopywriterOutput(BaseModel):
    contentRef: str         # where the caption/variants are stored
    caption: str
    hashtags: List[str] = Field(default_factory=list)
    extras: Dict = Field(default_factory=dict)
    mediaPlan: Dict = Field(default_factory=lambda: {"image": True})   # future: choose image/video

# Agent envelope (reuse ToolResult if desired)
