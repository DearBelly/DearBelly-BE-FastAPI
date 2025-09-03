import io
import pytest
from unittest.mock import patch, MagicMock

from app.services.s3_service import s3_service

class TestDownloadFile:
    @patch("app.services.s3_service.requests.get")
    def test_download_file_success(self, mock_get):
        # arrange
        mock_get.return_value = MagicMock()
        mock_get.return_value.content = b"test file content"
        mock_get.return_value.raise_for_status = MagicMock()

        # act
        obj = s3_service
        result = obj.download_file_from_presigned_url(
            "http://fake-url.com"
        )

        # assert
        assert isinstance(result, io.BytesIO)
        assert result.getvalue() == b"test file content"
        mock_get.assert_called_once_with(
            "http://fake-url.com"
        )
        mock_get.return_value.raise_for_status.assert_called_once()

    @patch("app.services.s3_service.requests.get")
    def test_download_file_http_error(self, mock_get):
        # arrange
        mock_get.return_value = MagicMock()
        mock_get.return_value.raise_for_status.side_effect = Exception("HTTP Error")

        obj = s3_service

        # act & assert
        with pytest.raises(Exception, match="HTTP Error"):
            obj.download_file_from_presigned_url("http://fake-url.com")