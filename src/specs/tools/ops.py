from pydantic import BaseModel, Field
from typing import Optional, Dict

class ImageGenRequest(BaseModel):
    prompt: str
    width: int = 1080
    height: int = 1350
    background: Optional[str] = None

class ImageGenResponse(BaseModel):
    status: str
    mediaRef: Optional[str] = None
    base64: Optional[str] = None
    meta: Dict = Field(default_factory=dict)

class PublishRequest(BaseModel):
    runTraceId: str
    brandId: str
    postPlanId: str
    contentRef: str
    mediaRef: str

class PublishResponse(BaseModel):
    status: str
    postId: Optional[str] = None
    meta: Dict = Field(default_factory=dict)
