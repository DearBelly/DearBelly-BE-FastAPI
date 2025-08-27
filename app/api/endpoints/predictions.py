from fastapi import APIRouter, Depends, Request
from app.schemas.job import JobRequest, ImageJob
from app.core.config import settings
import redis.asyncio as redis
import uuid
from datetime import datetime

router = APIRouter()

def get_redis_client(request: Request) -> redis.Redis:
    return request.app.state.redis_client

@router.post("/predict", status_code=202)
async def create_prediction_job(job_request: JobRequest, redis_client: redis.Redis = Depends(get_redis_client)):
    correlation_id = str(uuid.uuid4())
    job = ImageJob(
        correlationId=correlationId,
        presignedUrl=job_request.presigned_url,
        replyQueue=settings.STREAM_RESULT,
        callbackUrl=None,
        contentType="image/jpeg",
        createdAt=datetime.utcnow().isoformat(),
        ttlSec=3600,
    )

    await redis_client.xadd(
        settings.STREAM_JOB,
        {"json": job.model_dump_json()},
        maxlen=10_000,
        approximate=True,
    )

    return {"job_id": correlation_id}