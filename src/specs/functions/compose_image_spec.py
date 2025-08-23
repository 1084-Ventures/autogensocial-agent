
# compose_image_spec.py: defines request/response models for flexible image composition
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any, Tuple

class TextElement(BaseModel):
	text: str
	position: Tuple[int, int]  # (x, y) coordinates
	color: Optional[str] = None
	font: Optional[str] = None
	size: Optional[int] = None
	anchor: Optional[str] = None  # e.g., "left", "center", "right"

class ImageOverlay(BaseModel):
	image_url: HttpUrl
	position: Tuple[int, int]  # (x, y) coordinates
	size: Optional[Tuple[int, int]] = None  # (width, height)
	opacity: Optional[float] = None  # 0.0 to 1.0

class ComposeImageRequest(BaseModel):
	size: Optional[str] = Field(None, description="Image size, e.g., '1024x1024'")
	background_color: Optional[str] = None
	base_image_url: Optional[HttpUrl] = None
	text_elements: List[TextElement] = Field(default_factory=list)
	image_overlays: List[ImageOverlay] = Field(default_factory=list)
	output_destination: Optional[str] = Field(None, description="Where to store or return the image")
	additional_params: Optional[Dict[str, Any]] = None

class ComposeImageResponse(BaseModel):
	image_url: HttpUrl
	metadata: Optional[Dict[str, Any]] = None
