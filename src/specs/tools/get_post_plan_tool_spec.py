from pydantic import BaseModel
from typing import Optional
from ..documents.post_plan_document_spec import PostPlanDocument

class GetPostPlanRequest(BaseModel):
    post_plan_id: str

class GetPostPlanResponse(BaseModel):
    post_plan_document: Optional[PostPlanDocument]
