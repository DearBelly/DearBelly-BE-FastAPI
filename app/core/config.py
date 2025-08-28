from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

load_dotenv()

redis_url = os.getenv("REDIS_SERVER_URL")
bucket_name = os.getenv("BUCKET_NAME")
s3_region = os.getenv("S3_REGION")


class Settings(BaseSettings):
    REDIS_URL: str = redis_url
    S3_REGION: str = bucket_name
    BUCKET_NAME: str = s3_region

    STREAM_JOB: str = "image.jobs" # SpringBoot에서 job 발행 (FastAPI에서 listen)
    STREAM_RESULT: str = "image.results"  # FastAPI에서 결과 발행 (SpringBoot에서 listen)
    GROUP_NAME: str = "fastapi-workers" # FastAPI Consumer group name
    CONSUMER_NAME: str = "consumer-1"


settings = Settings()