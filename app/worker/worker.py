
import asyncio
import redis.asyncio as redis
from app.core.config import settings
from app.schemas.job import ImageJob
from app.worker.tasks import process_image_scan

class JobWorker:
    def __init__(self, redis_client: redis.Redis):
        self.redis_client = redis_client

    async def run(self):
        print(f"[worker] start consumer={settings.CONSUMER_NAME} group={settings.GROUP_NAME} stream={settings.STREAM_JOB}")
        reclaim_every_sec = 30
        last_reclaim = 0.0

        while True:
            try:
                resp = await self.redis_client.xreadgroup(
                    groupname=settings.GROUP_NAME,
                    consumername=settings.CONSUMER_NAME,
                    streams={settings.STREAM_JOB: ">"},
                    count=10,
                    block=5000,
                )
                if resp:
                    _, entries = resp[0]
                    for msg_id, fields in entries:
                        try:
                            job = ImageJob.model_validate_json(fields["json"])
                            asyncio.create_task(process_image_scan(job, self.redis_client))
                            await self.redis_client.xack(settings.STREAM_JOB, settings.GROUP_NAME, msg_id)
                        except Exception as e:
                            await self.redis_client.xadd(
                                f"{settings.STREAM_JOB}:DLQ",
                                {"id": msg_id, "error": str(e), **fields},
                            )

                now = asyncio.get_event_loop().time()
                if now - last_reclaim > reclaim_every_sec:
                    last_reclaim = now
                    _next, claimed = await self.redis_client.xautoclaim(
                        name=settings.STREAM_JOB,
                        groupname=settings.GROUP_NAME,
                        consumername=settings.CONSUMER_NAME,
                        min_idle_time=60_000,
                        start_id="0-0",
                        count=10,
                    )
                    for msg_id, fields in claimed:
                        try:
                            job = ImageJob.model_validate_json(fields["json"])
                            asyncio.create_task(process_image_scan(job, self.redis_client))
                            await self.redis_client.xack(settings.STREAM_JOB, settings.GROUP_NAME, msg_id)
                        except Exception as e:
                            await self.redis_client.xadd(
                                f"{settings.STREAM_JOB}:DLQ",
                                {"id": msg_id, "error": str(e), **fields},
                            )
            except asyncio.CancelledError:
                print("[worker] cancelled; bye")
                break
            except Exception as e:
                print(f"[worker] error: {e}")
                await asyncio.sleep(1)
