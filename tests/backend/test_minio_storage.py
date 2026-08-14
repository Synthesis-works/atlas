import pytest
from unittest.mock import patch, MagicMock
from apps.backend.services.storage import StorageService

@patch("apps.backend.services.storage.Minio")
def test_storage_service_upload(mock_minio):
    mock_client = MagicMock()
    mock_minio.return_value = mock_client
    
    service = StorageService()
    result = service.upload_text("test_obj.txt", "hello minio")
    
    assert result == "test_obj.txt"
    mock_client.put_object.assert_called_once()
    
@patch("apps.backend.services.storage.Minio")
def test_storage_service_download(mock_minio):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.read.return_value = b"hello minio"
    mock_client.get_object.return_value = mock_response
    mock_minio.return_value = mock_client
    
    service = StorageService()
    content = service.download_file("test_obj.txt")
    
    assert content == b"hello minio"
    mock_client.get_object.assert_called_once()

@patch("apps.backend.services.storage.Minio")
def test_storage_check_exists(mock_minio):
    mock_client = MagicMock()
    mock_minio.return_value = mock_client
    
    service = StorageService()
    assert service.check_exists("fake.txt") is True
    mock_client.stat_object.assert_called_once()
