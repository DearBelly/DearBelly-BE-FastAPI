import redis
from dotenv import load_dotenv
import os
from pydantic import BaseModel, Field
from typing import Any, Dict

load_dotenv()

redis_host = os.environment.get("REDIS_SERVER_HOST")

JOB_STREAM = "image.jobs"         # SpringBoot → FastAPI 작업 요청
RESULT_STREAM = "image.results"   # FastAPI → SpringBoot 결과

FASTAPI_GROUP = "fastapi-workers"     # FastAPI 그룹
SPRING_GROUP  = "spring-consumers"    # Spring Consumer 그룹
DLQ_RESULTS = "image.results.dlq"

redis_client = redis.Redis(
    host=redis_host, port=6379, encoding="UTF-8", decode_responses=True
)

class PublishRequest(BaseModel):
    stream: str = Field(default=JOB_STREAM, description="Redis Stream Job name")
    payload: Dict[str, Any]