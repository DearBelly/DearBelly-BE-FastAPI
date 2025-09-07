
from pydantic import BaseModel, Field

class JobRequest(BaseModel):
    presignedUrl: str = Field(..., description="다운로드할 이미지의 Presigned URL")

"""
FastAPI가 image.results Stream에 발행하는 메시지
"""
class JobResult(BaseModel):
    correlationId: str
    pillName: str
    isSafe: int
    description: str
    finishedAt: str

"""
Spring으로부터 받는 Job(image.jobs 구독)
"""
class ImageJob(BaseModel):
    correlationId: str = Field(alias="correlationId")
    presignedUrl: str = Field(alias="presignedUrl")
    replyQueue: str = Field(alias="replyQueue")
    contentType: str = Field(alias="contentType")
    createdAt: str = Field(alias="createdAt")
    ttlSec: int = Field(alias="ttlSec")
