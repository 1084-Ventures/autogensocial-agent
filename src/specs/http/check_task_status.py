from pydantic import BaseModel
from typing import Optional, Literal, Dict
from src.specs.common.ids import RunRef

class TaskStatusResponse(RunRef):
    currentPhase: Literal["orchestrate","copywriter","image","publish","completed","failed"]
    status: Literal["pending","in_progress","completed","failed"]
    isComplete: bool
    lastUpdateUtc: Optional[str] = None
    summary: Optional[Dict] = None
