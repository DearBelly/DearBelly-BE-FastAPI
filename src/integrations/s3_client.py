from typing import Optional
import boto3
from botocore.config import Config as BotoConfig

class S3Client:
    def __init__(self, region: Optional[str], endpoint_url: Optional[str] = None):
        session = boto3.session.Session(region_name=region)
        self.client = session.client(
            "s3",
            endpoint_url=endpoint_url,
            config=BotoConfig(
                retries={"max_attempts": 5, "mode": "standard"},
                read_timeout=30,
                connect_timeout=5,
            ),
        )

    def download_dir(self, bucket: str, prefix: str, local_dir: str):
        import os
        from pathlib import Path
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                rel = key[len(prefix) :].lstrip("/")
                dest = Path(local_dir) / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                self.client.download_file(bucket, key, str(dest))