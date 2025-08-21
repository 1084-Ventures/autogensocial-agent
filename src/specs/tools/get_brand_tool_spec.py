from pydantic import BaseModel, Field
from ..documents.brand_document_spec import BrandDocument

class GetBrandToolRequest(BaseModel):
	brand_id: str = Field(..., description="Unique identifier for the brand to retrieve")

class GetBrandToolResponse(BaseModel):
	brand_document: BrandDocument = Field(..., description="The retrieved brand document")
