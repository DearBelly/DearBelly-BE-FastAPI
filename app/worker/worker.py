
import asyncio
from app.worker.redis_client import redis_client
from app.core.config import settings
from app.schemas.job import ImageJob
from app.worker.tasks import process_image_scan

class JobWorker:
    def __init__(self, redis_client: redis_client):
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
                            task = asyncio.create_task(process_image_scan(job, redis_client))
                            print(f"[worker] {task} 발행 성공")
                            # 처리 성공 시에만 ack 후 del
                            task.add_done_callback(lambda t: asyncio.create_task(
                                self.redis_client.xack_and_del(settings.STREAM_JOB, settings.GROUP_NAME, msg_id)
                                if not t.exception() else
                                self.redis_client.xadd(f"{settings.STREAM_JOB}:DLQ",
                                                       {"id": msg_id, "error": str(t.exception()), **fields})
                            ))
                        except asyncio.CancelledError:
                            # 취소되면 재전송되도록 ack 하지 않음
                            raise
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
                            task = asyncio.create_task(process_image_scan(job, redis_client))
                            print(f"[worker] {task} 발행 성공")
                            # 처리 성공 시에만 ack 후 del
                            task.add_done_callback(lambda t: asyncio.create_task(
                                self.redis_client.xack_and_del(settings.STREAM_JOB, settings.GROUP_NAME, msg_id)
                                if not t.exception() else
                                self.redis_client.xadd(f"{settings.STREAM_JOB}:DLQ",
                                                       {"id": msg_id, "error": str(t.exception()), **fields})
                            ))
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
