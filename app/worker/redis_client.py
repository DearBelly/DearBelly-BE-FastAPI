import redis
from dotenv import load_dotenv
import os
from pydantic import BaseModel, Field
from typing import Any, Dict
from app.core.config import settings

load_dotenv()

redis_host = os.environ.get("REDIS_SERVER_HOST")

redis_client = redis.Redis(
    host=redis_host, port=6379, encoding="UTF-8", decode_responses=True
)

class PublishRequest(BaseModel):
    stream: str = Field(default=settings.JOB_STREAM, description="Redis Stream Job name")
    payload: Dict[str, Any]