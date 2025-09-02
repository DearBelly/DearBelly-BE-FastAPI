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
        await self.redis_client.xadd(stream_name, fields)

    # Group 단위로 읽어오기
    async def xreadgroup(
            self,
            group_name: str,
            consumer_name: str,
            stream_name: str,
            count: Optional[int] = None,
            block: Optional[int] = None,
            id: str = ">",
    ) -> List[tuple]:
        try:
            # Create the consumer group ( 존재하지 않을 때 )
            self.redis_client.xgroup_create(stream_name, group_name, id="$", mkstream=True)
        except redis.exceptions.ResponseError as e:
            # 이미 존재할 때
            if "BUSYGROUP" not in str(e):
                raise e

        response = self.redis_client.xreadgroup(
            groupname=group_name,
            consumername=consumer_name,
            streams={stream_name: id},
            count=count,
            block=block,
        )
        return response

    # Consumer 처리 완료
    def xack(self, stream_name: str, group_name: str, message_ids: List[str]) -> int:
        return self.redis_client.xack(stream_name, group_name, *message_ids)

    # 완료 시 삭제
    def xack_and_del(self, stream_name: str, group_name: str, message_ids: List[str]) -> int:

        acked_count = self.redis_client.xack(stream_name, group_name, *message_ids)

        # XACK가 성공하면 스트림에서 해당 메시지를 삭제 (XDEL)
        if acked_count > 0:
            self.redis_client.xdel(stream_name, *message_ids)

        return acked_count


    # 메시지 재처리 지원
    def xclaim(
            self,
            stream_name: str,
            group_name: str,
            consumer_name: str,
            min_idle_time: int,
            message_ids: List[str],
    ) -> List[tuple]:

        return self.redis_client.xclaim(
            name=stream_name,
            groupname=group_name,
            consumername=consumer_name,
            min_idle_time=min_idle_time,
            message_ids=message_ids,
        )

    def close(self):
        self.redis_client.disconnect()

redis_client = RedisStreamClient.init()