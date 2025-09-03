from __future__ import annotations

from pydantic import BaseModel


class AgentRegistryDocument(BaseModel):
    """Cosmos document for persisting agent IDs by logical name."""

    id: str
    logicalName: str
    agentId: str


__all__ = [
    "AgentRegistryDocument",
]

