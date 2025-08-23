from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from ..documents.post_document_spec import PostDocument

class GetPostsRequest(BaseModel):
    brand_id: str
    post_plan_id: Optional[str] = None
    fields: Optional[List[str]] = None  # Fields to return in each post document
    limit: Optional[int] = None  # Number of posts to look back on

class GetPostsResponse(BaseModel):
    posts: List[Dict[str, Any]]  # Each dict contains only the requested fields