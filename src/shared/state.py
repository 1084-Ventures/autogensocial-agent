import os
from typing import Any, Dict, Optional

from .state_file import FileRunStateStore
from .state_cosmos import CosmosRunStateStore, CosmosClient


def _select_backend():
    backend = os.getenv("RUN_STATE_BACKEND", "auto").lower()
    if backend == "file":
        return FileRunStateStore
    if backend == "cosmos":
        return CosmosRunStateStore
    if (
        os.getenv("COSMOS_DB_CONNECTION_STRING")
        and os.getenv("COSMOS_DB_NAME")
        and os.getenv("COSMOS_DB_CONTAINER_AGENT_RUNS")
        and CosmosClient is not None
    ):
        return CosmosRunStateStore
    return FileRunStateStore


RunStateStore = _select_backend()


def add_event(
    run_trace_id: str,
    *,
    phase: str,
    action: str,
    message: Optional[str] = None,
    status: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> None:
    try:
        RunStateStore.add_event(  # type: ignore[attr-defined]
            run_trace_id,
            phase=phase,
            action=action,
            message=message,
            status=status,
            data=data,
        )
    except AttributeError:
        pass
