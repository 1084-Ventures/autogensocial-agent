from pydantic import BaseModel
from datetime import datetime

class BaseDocument(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
