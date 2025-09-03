from __future__ import annotations

from dataclasses import dataclass
from typing import List, Type

from pydantic import BaseModel

from .models import (
    GetBrandRequest,
    GetBrandResponse,
    GetPostPlanRequest,
    GetPostPlanResponse,
)


@dataclass(frozen=True)
class ToolDef:
    name: str
    description: str
    input_model: Type[BaseModel]
    output_model: Type[BaseModel]


TOOLS: List[ToolDef] = [
    ToolDef(
        name="get_brand",
        description="Retrieve a brand document by id",
        input_model=GetBrandRequest,
        output_model=GetBrandResponse,
    ),
    ToolDef(
        name="get_post_plan",
        description="Retrieve a post plan document by id",
        input_model=GetPostPlanRequest,
        output_model=GetPostPlanResponse,
    ),
]
