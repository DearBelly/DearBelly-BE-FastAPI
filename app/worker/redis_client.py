import asyncio
import redis

from redis.asyncio import Redis as AsyncRedis
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, List
from app.core.config import settings

# Redis Stream Definition
class PublishRequest(BaseModel):
    stream: str = Field(default=settings.STREAM_JOB, description="Redis Stream Job name")
    payload: Dict[str, Any]

class RedisStreamClient:

    def __init__(self):
        self.redis_client = AsyncRedis.from_url(
            url=settings.REDIS_URL,
            decode_responses=True,
        )

    @classmethod
    def init(cls):
        broker = cls()
        return broker

    # Fast API 에서 Publish
    async def xadd(self, stream_name: str, fields: Dict[str, Any]) -> str:
        return await self.redis_client.xadd(stream_name, fields)

    # Group 단위로 읽어오기
    async def xreadgroup(
            self,
            group_name: str,
            consumer_name: str,
            stream_name: str,
            count: Optional[int] = None,
            block: Optional[int] = None,  # ms 단위
            id: str = ">",  # 새 메시지만 읽기
    ) -> List[tuple]:
        try:
            # Create the consumer group (존재하지 않을 때)
            self.redis_client.xgroup_create(
                stream_name, group_name, id="$", mkstream=True
            )
        except redis.exceptions.ResponseError as e:
            # 이미 존재할 때
            if "BUSYGROUP" not in str(e):
                raise

        streams = {stream_name: id}
        response = await self.redis_client.xreadgroup(
            group_name,  # groupname (positional)
            consumer_name,  # consumername (positional)
            streams,  # {stream: id} (positional)
            count=count,
            block=block,
        )
        return response

    # Consumer 처리 완료
    async def xack(self, stream_name: str, group_name: str, message_ids: List[str]) -> int:
        return await self.redis_client.xack(stream_name, group_name, *message_ids)

    # 완료 시 삭제
    async def xack_and_del(self, stream_name: str, group_name: str, message_ids: str) -> int:

        acked_count = await self.redis_client.xack(stream_name, group_name, *message_ids)

        # XACK가 성공하면 스트림에서 해당 메시지를 삭제 (XDEL)
        if acked_count > 0:
            await self.redis_client.xdel(stream_name, *message_ids)

        return acked_count

    async def xgroup_create(self, stream_name: str, group_name: str, id: str = "$") -> bool:
        try:
            self.redis_client.xgroup_create(stream_name, group_name, id, mkstream=True)
            return True
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                print(f"Consumer group '{group_name}' already exists.")
                return False
            raise e

    # 메시지 재처리 지원
    async def xclaim(
            self,
            stream_name: str,
            group_name: str,
            consumer_name: str,
            min_idle_time: int,
            message_ids: List[str],
    ) -> List[tuple]:

        return await self.redis_client.xclaim(
            stream_name=stream_name,
            group_name=group_name,
            consumer_name=consumer_name,
            min_idle_time=min_idle_time,
            message_ids=message_ids,
        )

    async def aclose(self):
        await self.redis_client.close()

redis_client = RedisStreamClient.init()