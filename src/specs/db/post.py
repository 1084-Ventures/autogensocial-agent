from pydantic import BaseModel, Field
from typing import Optional, Dict, List

class PostDoc(BaseModel):
    id: str                 # postId
    partitionKey: str       # brandId
    runTraceId: str
    brandId: str
    postPlanId: str
    contentRef: str
    mediaRef: str
    caption: str
    hashtags: List[str] = Field(default_factory=list)
    status: str = "published"
    improvement: Optional[Dict] = None
    metrics: Optional[Dict] = None
    vitality: Optional[Dict] = None
    createdAtUtc: str
    _ts: Optional[int] = Field(default=None)
