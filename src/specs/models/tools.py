from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel
from .domain import BrandDocument, PostPlanDocument


class ErrorInfo(BaseModel):
    code: str
    message: str


class ToolResultEnvelope(BaseModel):
    """Standardized envelope for tool outputs."""

    status: Literal["completed", "failed"]
    result: Optional[Dict[str, Any]] = None
    error: Optional[ErrorInfo] = None
    meta: Optional[Dict[str, Any]] = None


class GetBrandRequest(BaseModel):
    brandId: str
    # Optional trace correlation; include when available
    runTraceId: Optional[str] = None


class GetBrandResult(BaseModel):
    brand: BrandDocument


class GetBrandResponse(ToolResultEnvelope):
    # Narrow the envelope's result to a typed structure
    result: Optional[GetBrandResult] = None


class GetPostPlanRequest(BaseModel):
    postPlanId: str
    runTraceId: Optional[str] = None


class GetPostPlanResult(BaseModel):
    postPlan: PostPlanDocument


class GetPostPlanResponse(ToolResultEnvelope):
    result: Optional[GetPostPlanResult] = None


__all__ = [
    "ErrorInfo",
    "ToolResultEnvelope",
    "BrandDocument",
    "GetBrandRequest",
    "GetBrandResult",
    "GetBrandResponse",
    "PostPlanDocument",
    "GetPostPlanRequest",
    "GetPostPlanResult",
    "GetPostPlanResponse",
]
