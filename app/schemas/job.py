
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
    correlation_id: str = Field(alias="correlationId")
    presigned_url: str = Field(alias="presignedUrl")
    reply_queue: str = Field(alias="replyQueue")
    callback_url: str | None = Field(alias="callbackUrl")
    content_type: str = Field(alias="contentType")
    created_at: str = Field(alias="createdAt")
    ttl_sec: int = Field(alias="ttlSec")
