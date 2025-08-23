from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from ..common.base_document_spec import BaseDocument
from ..common.enums import Platform, PostStatus

class PostMediaItem(BaseModel):
	media_number: int = Field(..., description="Order or identifier for the media item")
	media_quote: Optional[str] = Field(None, description="Quote or caption for the media item")
	media_description: Optional[str] = Field(None, description="Description of the media item")
	media_url: Optional[HttpUrl] = Field(None, description="URL to the media file (image/video)")
	sound_url: Optional[HttpUrl] = Field(None, description="URL to an associated sound or audio file")

class PostContent(BaseModel):
	media_type: str = Field(..., description="Type of media, e.g., image, video, carousel")
	topic: str = Field(..., description="Main topic or theme of the post")
	comment: Optional[str] = Field(None, description="Comment or main text for the post")
	hashtags: List[str] = Field(default_factory=list, description="List of hashtags for the post")
	media: List[PostMediaItem] = Field(default_factory=list, description="List of media items attached to the post")
	call_to_action: Optional[str] = Field(None, description="Call to action for the post")
	mentions: Optional[List[str]] = Field(None, description="Usernames or handles to mention in the post")
	language: Optional[str] = Field(None, description="Language of the post content")
	location: Optional[str] = Field(None, description="Location or geo-tag for the post")

class PostDocument(BaseDocument):
	brand_id: str = Field(..., description="ID of the brand this post belongs to")
	post_plan_id: Optional[str] = Field(None, description="ID of the post plan this post is associated with")
	content: PostContent = Field(..., description="Structured content for the post")
	platforms: List[Platform] = Field(..., description="Platforms where the post will be published")
	status: PostStatus = Field(..., description="Current status of the post in the workflow")
	scheduled_time: Optional[datetime] = Field(None, description="Scheduled time for publishing the post")
	published_time: Optional[datetime] = Field(None, description="Actual time the post was published")
	scheduled_by: Optional[str] = Field(None, description="User or agent who scheduled the post")
	metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata for the post")
