
from pydantic import BaseModel, Field

class JobRequest(BaseModel):
    presigned_url: str = Field(..., description="다운로드할 이미지의 Presigned URL")

class JobResult(BaseModel):
    pill_name: str
    correlation_id: str
    label: str
    confidence: float
    finished_at: str

class ImageJob(BaseModel):
    correlationId: str
    presignedUrl: str
    replyQueue: str
    callbackUrl: str | None = None
    contentType: str
    createdAt: str
    ttlSec: int
