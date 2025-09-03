from __future__ import annotations

from typing import Dict, Type

from pydantic import BaseModel

from .http import OrchestrateRequest, DurableOrchestrationStartResponse
from .activities import CopywriterActivityPayload, ContentRefResult
from .tools import (
    ErrorInfo,
    ToolResultEnvelope,
    GetBrandRequest,
    GetBrandResult,
    GetBrandResponse,
)
from .domain import BrandDocument, PostPlanDocument
from .persistence import AgentRegistryDocument


# Registry mapping output schema filenames to models for generation
SCHEMA_MODELS: Dict[str, Type[BaseModel]] = {
    "orchestrate.request.schema.json": OrchestrateRequest,
    "copywriter.activity.payload.schema.json": CopywriterActivityPayload,
    "contentref.result.schema.json": ContentRefResult,
    "tool.envelope.schema.json": ToolResultEnvelope,
    "error.info.schema.json": ErrorInfo,
    "agent.registry.schema.json": AgentRegistryDocument,
    "durable.start.response.schema.json": DurableOrchestrationStartResponse,
    "brand.document.schema.json": BrandDocument,
    "get_brand.request.schema.json": GetBrandRequest,
    "get_brand.result.schema.json": GetBrandResult,
    "get_brand.response.schema.json": GetBrandResponse,
    "postplan.document.schema.json": PostPlanDocument,
    "get_post_plan.request.schema.json": GetPostPlanRequest,
    "get_post_plan.result.schema.json": GetPostPlanResult,
    "get_post_plan.response.schema.json": GetPostPlanResponse,
}

__all__ = [
    "OrchestrateRequest",
    "CopywriterActivityPayload",
    "ContentRefResult",
    "ToolResultEnvelope",
    "ErrorInfo",
    "AgentRegistryDocument",
    "DurableOrchestrationStartResponse",
    "BrandDocument",
    "GetBrandRequest",
    "GetBrandResult",
    "GetBrandResponse",
    "PostPlanDocument",
    "GetPostPlanRequest",
    "GetPostPlanResult",
    "GetPostPlanResponse",
    "SCHEMA_MODELS",
]
