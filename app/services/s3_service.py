
import requests
from io import BytesIO

class S3Service:
    def __init__(self):
        pass

    def download_file_from_presigned_url(self, presigned_url: str) -> BytesIO:
        response = requests.get(presigned_url)
        response.raise_for_status()
        # response의 content를 BytesIO로 감싸 반환
        return BytesIO(response.content)

s3_service = S3Service()
