import logging
from typing import Any, Dict, Optional


_LOGGER = logging.getLogger("autogensocial")


def log(level: int, run_trace_id: Optional[str], message: str, **dimensions: Any) -> None:
    dims: Dict[str, Any] = {"runTraceId": run_trace_id} if run_trace_id else {}
    dims.update(dimensions)
    try:
        _LOGGER.log(level, message, extra={"custom_dimensions": dims})
    except Exception:
        # Fallback if extra/custom_dimensions not supported in the environment
        _LOGGER.log(level, f"{message} | {dims}")


def info(run_trace_id: Optional[str], message: str, **dimensions: Any) -> None:
    log(logging.INFO, run_trace_id, message, **dimensions)


def error(run_trace_id: Optional[str], message: str, **dimensions: Any) -> None:
    log(logging.ERROR, run_trace_id, message, **dimensions)

