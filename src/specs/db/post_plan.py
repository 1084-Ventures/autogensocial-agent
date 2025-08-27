from pydantic import BaseModel, Field
from typing import Optional, Dict, List

class PostPlanDoc(BaseModel):
    id: str                 # postPlanId
    partitionKey: str       # brandId
    brandId: str
    brief: Dict = Field(default_factory=dict)        # campaign goal, angle, references
    constraints: Dict = Field(default_factory=dict)  # quiet hours, embargo, etc.
    mediaPrefs: Dict = Field(default_factory=dict)   # aspect, style, brand rules
    status: str = "active"
    _ts: Optional[int] = Field(default=None)
