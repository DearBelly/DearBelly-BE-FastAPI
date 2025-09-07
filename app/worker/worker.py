import json
import asyncio
from app.worker.redis_client import redis_client
from app.core.config import settings
from app.schemas.job import ImageJob
from app.worker.tasks import process_image_scan

"""
Redis Stream에 정의한 유효한 형식 메시지를 위한 전처리 함수
"""
def _to_scalr(v):
    # XADD 허용 타입: str, bytes, int, float
    if isinstance(v, (str, bytes, int, float)):
        return v
    # 그 외는 JSON str
    return json.dumps(v, ensure_ascii=False)

"""
Decoding
"""
def _decode(b):
    if isinstance(b, (bytes, bytearray)):
        return b.decode()
    else:
        return b


def _sanitize_fields_for_xadd(fields: dict) -> dict:
    # 정제
    cleaned = {}
    for k, v in fields.items():
        k = _decode(k)
        if isinstance(v, (bytes, bytearray)):
            try:
                v = v.decode()
            except Exception:
                pass
        else:
            v = _to_scalr(v)
        cleaned[k] = v
    return cleaned


"""
"image.jobs"를 구독
"""
class JobWorker:
    def __init__(self, redis_client: redis_client):
        self.redis_client = redis_client

    async def run(self):
        print(f"[worker] start consumer={settings.CONSUMER_NAME} group={settings.GROUP_NAME} stream={settings.STREAM_JOB}")
        reclaim_every_sec = 30
        last_reclaim = 0.0

        while True:
            try:
                # Consumer의 메시지 읽기
                resp = await self.redis_client.xreadgroup(
                    group_name=settings.GROUP_NAME,
                    consumer_name=settings.CONSUMER_NAME,
                    stream_name=settings.STREAM_JOB,
                    count=10,
                    block=5000,
                )
                if resp:
                    _, entries = resp[0]
                    for msg_id, fields in entries:
                        try:
                            job_type = fields.get(b"type") or fields.get("type")
                            correlation_id = fields.get(b"correlationId") or fields.get("correlationId")
                            payload = fields.get(b"payload") or fields.get("payload")

                            # type 검증
                            if job_type in (b"image_jobs", "image_jobs"):

                                # payload 전처리
                                if isinstance(payload, (bytes, bytearray)):
                                    payload_str = payload.decode()
                                else:
                                    payload_str = payload if isinstance(payload, str) else json.dumps(payload)

                                # 최종 반환 data
                                data = json.loads(payload_str)
                                print(f"Job received id={msg_id} correlationId={correlation_id} payload={data}")

                                job = data
                                # XADD까지 호출
                                task = asyncio.create_task(process_image_scan(job, redis_client))
                                print(f"[worker] {task} 발행 성공")

                                # 처리 성공 시에만 ack 후 del
                                task.add_done_callback(lambda t: asyncio.create_task(
                                    self.redis_client.xack_and_del(settings.STREAM_JOB, settings.GROUP_NAME, msg_id)
                                    if not t.exception() else
                                    self.redis_client.xadd(f"{settings.STREAM_JOB}:DLQ",
                                                           {"id": msg_id, "error": str(t.exception()), **fields})
                                ))

                            else:
                                # job_type 불일치 경우 -> DLQ
                                clean = _sanitize_fields_for_xadd(fields)
                                clean.update({"id": _decode(msg_id), "error": "unexpected job type"})
                                await self.redis_client.xadd(f"{settings.STREAM_JOB}:DLQ", clean)

                        except asyncio.CancelledError:
                            # 취소되면 재전송되도록 ack 하지 않음
                            raise

                        except Exception as e:
                            clean = _sanitize_fields_for_xadd(fields)
                            clean.update({"id": _decode(msg_id), "error": str(e)})
                            await self.redis_client.xadd(f"{settings.STREAM_JOB}:DLQ", clean)

                # 주기적으로 AutoClaim
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
                            payload = fields.get(b"payload") or fields.get("payload")
                            if isinstance(payload, (bytes, bytearray)):
                                payload = payload.decode()
                            job = ImageJob.model_validate_json(payload)

                            task = asyncio.create_task(process_image_scan(job, self.redis_client))
                            print(f"[worker] {task} 발행 성공")

                            def _on_done(t: asyncio.Task, *, msg_id=msg_id, fields=fields):
                                async def _ack_or_dlq():
                                    exc = t.exception()
                                    if exc is None:
                                        await self.redis_client.xack_and_del(settings.STREAM_JOB, settings.GROUP_NAME,
                                                                             msg_id)
                                    else:
                                        clean = _sanitize_fields_for_xadd(fields)
                                        clean.update({"id": _decode(msg_id), "error": str(exc)})
                                        await self.redis_client.xadd(f"{settings.STREAM_JOB}:DLQ", clean)

                                asyncio.create_task(_ack_or_dlq())

                            task.add_done_callback(_on_done)

                        except Exception as e:
                            clean = _sanitize_fields_for_xadd(fields)
                            clean.update({"id": _decode(msg_id), "error": str(e)})
                            await self.redis_client.xadd(f"{settings.STREAM_JOB}:DLQ", clean)

            except asyncio.CancelledError:
                print("[worker] cancelled; bye")
                break
            except Exception as e:
                print(f"[worker] error: {e}")
                await asyncio.sleep(1)
