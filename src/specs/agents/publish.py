from pydantic import BaseModel


class PublishInput(BaseModel):
    runTraceId: str
    brandId: str
    postPlanId: str
    contentRef: str
    mediaRef: str


class PublishOutput(BaseModel):
    postId: str
    publishedAtUtc: str
    contentRef: str
    mediaRef: str

