from pydantic import BaseModel

class RunRef(BaseModel):
    runTraceId: str

class EntityIds(BaseModel):
    brandId: str
    postPlanId: str