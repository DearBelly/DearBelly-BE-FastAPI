
import boto3
from botocore.config import Config as BotoConfig
import requests
from io import BytesIO

from app.core.config import settings

class S3Service:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            config=BotoConfig(
                retries={"max_attempts": 5, "mode": "standard"},
                read_timeout=30,
                connect_timeout=5,
            ),
        )

    def download_file_from_presigned_url(self, presigned_url: str) -> BytesIO:
        response = requests.get(presigned_url)
        response.raise_for_status()

        return BytesIO(response.content) # response 안의 content Stream으로 처리

s3_service = S3Service()
