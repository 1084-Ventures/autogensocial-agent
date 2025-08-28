from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class Agent(ABC):
    """Abstract base class for all agents.

    Provides a standard ``run`` interface and support for attaching a
    ``run_trace_id`` used for logging or state tracking.
    """

    def __init__(self) -> None:
        self._run_trace_id: str | None = None

    def with_run_trace(self, run_trace_id: str) -> "Agent":
        """Attach a runTraceId for downstream logging."""

        self._run_trace_id = run_trace_id
        return self

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the agent and return its structured output."""


__all__ = ["Agent"]
