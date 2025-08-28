import redis
from pydantic import BaseModel, Field
from typing import Any, Dict
from app.core.config import settings

redis_client = redis.asyncio.from_url(settings.REDIS_URL, decode_responses=True)

class PublishRequest(BaseModel):
    stream: str = Field(default=settings.JOB_STREAM, description="Redis Stream Job name")
    payload: Dict[str, Any]