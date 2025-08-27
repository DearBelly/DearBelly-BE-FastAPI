from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    REDIS_URL: str = os.environ.get("REDIS_SERVER_URL", "redis://localhost:6379")
    S3_REGION: str = os.environ.get("S3_REGION", "ap-northeast-2")
    S3_ENDPOINT_URL: str | None = os.environ.get("S3_ENDPOINT_URL")
    BUCKET_NAME: str = os.environ.get("BUCKET_NAME")

    STREAM_JOB: str = "image.jobs"
    STREAM_RESULT: str = "image.results"
    GROUP_NAME: str = "fastapi-workers"
    CONSUMER_NAME: str = "consumer-1"


settings = Settings()