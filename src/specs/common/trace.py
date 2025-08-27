from pydantic import BaseModel
from typing import Optional, Literal, Dict

class PhaseLog(BaseModel):
    runTraceId: str
    phase: Literal["orchestrate","copywriter","image","publish","analytics","planner","video"]
    status: Literal["received","started","completed","failed"]
    details: Optional[Dict] = None