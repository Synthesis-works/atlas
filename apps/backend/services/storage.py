import io
import uuid
from typing import Optional

from minio import Minio
from minio.error import S3Error

from apps.backend.config import settings


class StorageService:
    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure
        )
        self.bucket_name = settings.minio_bucket
        self._ensure_bucket()
        
    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except Exception:
            # In a production app, logger should be used here.
            pass

    def upload_file(self, object_name: str, file_data: bytes, content_type: str = "application/octet-stream") -> str:
        """
        Uploads file data and returns the object key.
        """
        data_stream = io.BytesIO(file_data)
        length = len(file_data)
        self.client.put_object(
            self.bucket_name,
            object_name,
            data_stream,
            length=length,
            content_type=content_type
        )
        return object_name

    def upload_text(self, object_name: str, text: str, content_type: str = "text/plain") -> str:
        """
        Convenience method to upload strings.
        """
        return self.upload_file(object_name, text.encode("utf-8"), content_type=content_type)

    def get_presigned_url(self, object_name: str) -> str:
        """
        Returns a temporary URL to securely fetch the object without streaming it through the backend server.
        """
        return self.client.presigned_get_object(self.bucket_name, object_name)

    def download_file(self, object_name: str) -> Optional[bytes]:
        """
        Downloads a file synchronously directly into memory.
        """
        response = None
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            return response.read()
        except S3Error:
            return None
        finally:
            if response:
                response.close()
                response.release_conn()

    def check_exists(self, object_name: str) -> bool:
        """
        Checks if the artifact exists in MinIO.
        """
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False
