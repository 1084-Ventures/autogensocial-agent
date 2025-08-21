from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional, List, Literal
from datetime import datetime
from ..common.constants import SOCIAL_PLATFORMS
from ..common.base_document_spec import BaseDocument

class PostPlanInfo(BaseModel):
	name: str
	description: str
	type: List[Literal["image", "multi-image", "video"]]
	platforms: List[str]

	@field_validator("platforms", mode="before")
	@classmethod
	def validate_platforms(cls, values):
		for value in values:
			if value not in SOCIAL_PLATFORMS:
				raise ValueError(f"Each platform must be one of {SOCIAL_PLATFORMS}, got '{value}'")
		return values

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
