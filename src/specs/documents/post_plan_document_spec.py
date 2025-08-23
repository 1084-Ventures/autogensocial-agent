from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, List, Literal
from datetime import datetime
from ..common.enums import Platform
from ..common.base_document_spec import BaseDocument

class PostPlanInfo(BaseModel):
	name: str
	description: str
	type: List[Literal["image", "multi-image", "video"]]
	platforms: List[Platform]


class PostPlanSchedule(BaseModel):
	frequency: str
	start_date: str  # ISO date string
	end_date: str    # ISO date string

class PostPlanContent(BaseModel):
	topics: List[str]
	hashtags: List[str]

class PostPlan(BaseModel):
	info: PostPlanInfo
	schedule: PostPlanSchedule
	content: PostPlanContent

class ExecutionHistoryItem(BaseModel):
	executed_at: datetime
	status: str
	details: Optional[str] = None

class PostPlanDocument(BaseDocument):
	brand_id: str
	post_plan: PostPlan
	last_executed_at: Optional[datetime] = None
	status: str
	execution_history: List[ExecutionHistoryItem] = []
