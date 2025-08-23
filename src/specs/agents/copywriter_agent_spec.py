# CopywriterAgent spec: defines request/response models for the agent
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from ..documents.brand_document_spec import BrandDocument
from ..documents.post_plan_document_spec import PostPlanDocument
from ..documents.post_document_spec import PostMediaItem
from ..documents.post_document_spec import PostContent
from ..tools.get_posts_tool_spec import GetPostsResponse
from ..common.response_base import ResponseBase

class CopywriterAgentRequest(BaseModel):
	brand_document: BrandDocument = Field(..., description="The brand document for which to generate content")
	post_plan_document: PostPlanDocument = Field(..., description="The post plan document guiding content creation")
	previous_posts: Optional[GetPostsResponse] = Field(None, description="Recent posts for reference")
	run_trace_id: Optional[str] = Field(None, description="Trace/session identifier for logging and tracing")

class CopywriterAgentResponse(ResponseBase):
	post_content: PostContent = Field(..., description="Structured content for the post")
	metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata about the generated content")
