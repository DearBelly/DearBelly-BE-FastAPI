
import boto3
from botocore.config import Config as BotoConfig
from pathlib import Path
import requests

from app.core.config import settings

class S3Service:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            endpoint_url=settings.S3_ENDPOINT_URL,
            config=BotoConfig(
                retries={"max_attempts": 5, "mode": "standard"},
                read_timeout=30,
                connect_timeout=5,
            ),
        )

    def download_file_from_presigned_url(self, presigned_url: str, destination: Path):
        response = requests.get(presigned_url)
        response.raise_for_status()
        with open(destination, "wb") as f:
            f.write(response.content)

s3_service = S3Service()
