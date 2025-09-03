from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CopywriterActivityPayload(BaseModel):
    brandId: str = Field(min_length=1)
    postPlanId: str = Field(min_length=1)
    runTraceId: Optional[str] = None


class ContentRefResult(BaseModel):
    contentRef: str = Field(min_length=1)


__all__ = [
    "CopywriterActivityPayload",
    "ContentRefResult",
]

