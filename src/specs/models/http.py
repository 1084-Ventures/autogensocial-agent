from __future__ import annotations

from pydantic import BaseModel, Field


class OrchestrateRequest(BaseModel):
    """Request payload or query params for starting the orchestration."""

    brandId: str = Field(min_length=1)
    postPlanId: str = Field(min_length=1)


class DurableOrchestrationStartResponse(BaseModel):
    """Response body returned by Durable Functions when starting an orchestration.

    This matches the structure produced by `create_check_status_response`.
    """

    id: str
    statusQueryGetUri: str
    sendEventPostUri: str
    purgeHistoryDeleteUri: str
    terminatePostUri: str

__all__ = [
    "OrchestrateRequest",
    "DurableOrchestrationStartResponse",
]

