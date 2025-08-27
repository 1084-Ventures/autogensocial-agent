from pydantic import BaseModel
from typing import Optional, Dict, List

class GetBrandRequest(BaseModel):
    brandId: str

class GetBrandResponse(BaseModel):
    status: str
    document: Optional[Dict] = None

class GetPostPlanRequest(BaseModel):
    brandId: str
    postPlanId: str

class GetPostPlanResponse(BaseModel):
    status: str
    document: Optional[Dict] = None

class GetPostsRequest(BaseModel):
    brandId: str
    limit: int = 10

class GetPostsResponse(BaseModel):
    status: str
    items: List[Dict]