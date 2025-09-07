
import asyncio
import redis.asyncio as redis
from datetime import datetime

from app.core.config import settings
from app.schemas.job import ImageJob, JobResult
from app.services.predictor_service import predictor_service
from app.services.s3_service import s3_service

"""
이미지를 다운 -> 다운 한 것에 대하여 모델 분석 요청
"""
async def process_image_scan(job: ImageJob, redis_client: redis.Redis):
    correlationId = job.correlationId
    print(f"[task] Start image scan for job_id={correlationId}")
    try:

        stream_file = await asyncio.to_thread(
            s3_service.download_file_from_presigned_url,
            job.presignedUrl
        )

        stream_file.seek(0)

        pillName, label, confidence = await asyncio.to_thread(
            predictor_service.predict,
            stream_file
        )

        # TODO: ChatGPT에 요청 결과 출력

        isSafe = 0
        description = "일단은 테스트입니다. 추후에 GPT 부분 추가할 예정"
        finishedAt = datetime.utcnow().isoformat()

        result = JobResult(
            correlationId=correlationId,
            pillName=pillName,
            isSafe=isSafe,
            description=description,
            finishedAt=finishedAt,
        )

        await redis_client.xadd(
            settings.STREAM_RESULT,
            {
                "correlationId": correlationId,
                "type": "image_results",
                "payload": result.model_dump_json()},
            maxlen=10_000,
            approximate=True,
        )

        print(f"[task] Image scan successfully finished for job_id={correlationId}")

    except Exception as e:
        print(f"[task] Failed to process job_id={correlationId}: {e}")
    finally:
        print(f"[task] Image scan finished for job_id={correlationId}")
