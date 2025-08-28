from pydantic import BaseModel, Field
from typing import Optional, Dict, Literal
from src.specs.common.ids import RunRef, EntityIds


class QueueRefs(BaseModel):
    contentRef: Optional[str] = None  # e.g., Cosmos ID for generated copy
    mediaRef: Optional[str] = None  # e.g., Blob URL or Cosmos ID for image


class QueueMessage(RunRef, EntityIds):
    step: Literal["generate_content", "generate_image", "publish"]
    agent: Literal["copywriter", "composer-image", "none"] = "none"
    refs: QueueRefs = Field(default_factory=QueueRefs)
    args: Dict = Field(default_factory=dict)


