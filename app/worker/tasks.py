
import asyncio
import json
from pathlib import Path
import redis.asyncio as redis
from datetime import datetime

from app.core.config import settings
from app.schemas.job import ImageJob, JobResult
from app.services.predictor_service import predictor_service
from app.services.s3_service import s3_service

async def process_image_scan(job: ImageJob, redis_client: redis.Redis):
    correlation_id = job.correlationId
    print(f"[task] Start image scan for job_id={correlation_id}")

    temp_image_path = Path(f"/tmp/{correlation_id}.jpg")

    try:
        s3_service.download_file_from_presigned_url(job.presignedUrl, temp_image_path)

        pill_name, label, confidence = predictor_service.predict(temp_image_path)

        finished_at = datetime.utcnow().isoformat()

        result = JobResult(
            pill_name=pill_name,
            correlation_id=correlation_id,
            label=label,
            confidence=confidence,
            finished_at=finished_at,
        )

        await redis_client.xadd(
            settings.STREAM_RESULT,
            {"json": result.model_dump_json()},
            maxlen=10_000,
            approximate=True,
        )

        print(f"[task] Image scan finished for job_id={correlation_id}")

    except Exception as e:
        print(f"[task] Failed to process job_id={correlation_id}: {e}")
    finally:
        if temp_image_path.exists():
            temp_image_path.unlink()
