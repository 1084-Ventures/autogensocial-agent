import time
from typing import Callable, Tuple, TypeVar

T = TypeVar("T")


def retry_with_backoff(
    operation: Callable[[], T],
    *,
    attempts: int = 3,
    delay: float = 1.5,
    backoff: float = 1.5,
    exceptions: Tuple[type, ...] = (Exception,),
) -> T:
    """Execute `operation` with simple exponential backoff."""
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return operation()
        except exceptions as exc:  # type: ignore[arg-type]
            last_exc = exc
            if attempt == attempts - 1:
                raise
            time.sleep(delay)
            delay *= backoff
    assert last_exc is not None
    raise last_exc
