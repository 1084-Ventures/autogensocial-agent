from pydantic import BaseModel, Field
from typing import Optional, Dict

class BrandDoc(BaseModel):
    id: str                 # brandId
    partitionKey: str       # brandId
    name: str
    voice: Dict = Field(default_factory=dict)
    colors: Dict = Field(default_factory=dict)
    platforms: Dict = Field(default_factory=dict)
    _ts: Optional[int] = Field(default=None, description="Cosmos server timestamp")
