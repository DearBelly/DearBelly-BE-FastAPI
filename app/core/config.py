from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379")
    S3_REGION: str = os.environ.get("S3_REGION", "ap-northeast-2")
    BUCKET_NAME: str = os.environ.get("BUCKET_NAME")

    STREAM_JOB: str = "image.jobs" # SpringBoot에서 job 발행 (FastAPI에서 listen)
    STREAM_RESULT: str = "image.results"  # FastAPI에서 결과 발행 (SpringBoot에서 listen)
    GROUP_NAME: str = "fastapi-workers" # FastAPI Consumer group name
    CONSUMER_NAME: str = "consumer-1"


settings = Settings()