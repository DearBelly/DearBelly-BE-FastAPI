import redis
import json

from redis.asyncio import Redis as AsyncRedis
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union
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
        return cls()

    @staticmethod
    def _to_scalar(v: Any) -> Union[str, bytes, int, float]:
        # Redis XADD : str/bytes/int/float 허용
        if isinstance(v, (str, bytes, int, float)):
            return v
        # 그 외는 JSON 문자열로 직렬화 (ensure_ascii=False로 한글 보존)
        return json.dumps(v, ensure_ascii=False)


    @classmethod
    def _sanitize_fields_for_xadd(cls, fields: Dict[str, Any]) -> Dict[str, Union[str, bytes, int, float]]:
        clean: Dict[str, Union[str, bytes, int, float]] = {}
        for k, v in fields.items():
            if not isinstance(k, str):
                k = str(k)
            clean[k] = cls._to_scalar(v)
        return clean


    # Fast API 에서 Publish
    async def xadd(
        self,
        stream_name: str,
        fields: Dict[str, Any],
        *,
        maxlen: Optional[int] = 10_000,
        approximate: bool = True,
        nomkstream: bool = False,
        id: str = "*",
    ) -> str:
        safe_fields = self._sanitize_fields_for_xadd(fields)
        return await self.redis_client.xadd(
            stream_name,
            safe_fields,
            id=id,
            maxlen=maxlen,
            approximate=approximate,
            nomkstream=nomkstream,
        )

    # Group 단위로 읽어오기
    async def xreadgroup(
        self,
        group_name: str,
        consumer_name: str,
        stream_name: str,
        count: Optional[int] = None,
        block: Optional[int] = None,  # ms
    ) -> List[tuple]:
        # Consumer Group 생성 (없으면)
        try:
            await self.redis_client.xgroup_create(
                name=stream_name,
                groupname=group_name,
                id="0",
                mkstream=True,
            )
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        streams = {stream_name: ">"} # 신규 메시지
        response = await self.redis_client.xreadgroup(
            group_name,
            consumer_name,
            streams,
            count=count,
            block=block,
        )
        return response

    # Consumer 처리 완료
    async def xack(self, stream_name: str, group_name: str, message_ids: List[str]) -> int:
        return await self.redis_client.xack(stream_name, group_name, *message_ids)

    # 완료 시 삭제
    async def xack_and_del(
        self,
        stream_name: str,
        group_name: str,
        message_ids: Union[str, List[str]],
    ) -> int:
        ids = [message_ids] if isinstance(message_ids, str) else list(message_ids)
        acked_count = await self.redis_client.xack(stream_name, group_name, *ids)
        if acked_count > 0:
            await self.redis_client.xdel(stream_name, *ids)
        return acked_count

    # Group 생성
    async def xgroup_create(self, stream_name: str, group_name: str, id: str = "$") -> bool:
        try:
            await self.redis_client.xgroup_create(stream_name, group_name, id, mkstream=True)
            return True
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                print(f"Consumer group '{group_name}' already exists.")
                return False
            raise

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

    # 자동으로 재청구
    async def xautoclaim(
            self,
            name: str,
            groupname: str,
            consumername: str,
            min_idle_time: int,
            start_id: str = "0-0",
            count: Optional[int] = None,
            justid: bool = False,
    ):
        res = await self.redis_client.xautoclaim(
            name=name,
            groupname=groupname,
            consumername=consumername,
            min_idle_time=min_idle_time,
            start_id=start_id,
            count=count,
            justid=justid,
        )
        # 2-튜플/3-튜플 호환하도록 전처리
        if isinstance(res, (list, tuple)) and len(res) == 3:
            next_id, messages, _deleted = res
            return next_id, messages
        return res


    # 종료
    async def aclose(self):
        await self.redis_client.close()

redis_client = RedisStreamClient.init()