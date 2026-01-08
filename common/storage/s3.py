"""S3-compatible storage backend (AWS S3, GCS, MinIO)."""
from pathlib import Path
from typing import List, Optional
from .backend import StorageBackend


class S3Storage(StorageBackend):
    """S3-compatible storage (works with AWS, GCS HMAC, MinIO)."""
    
    def __init__(
        self,
        bucket: str,
        endpoint_url: Optional[str] = None,  # For GCS/MinIO
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
    ):
        self.bucket = bucket
        self.endpoint_url = endpoint_url
        # TODO: Initialize boto3 client
    
    def upload(self, local_path: Path, remote_path: str) -> str:
        # TODO: Implement with boto3
        raise NotImplementedError
    
    def download(self, remote_path: str, local_path: Path) -> Path:
        raise NotImplementedError
    
    def list(self, prefix: str = '') -> List[str]:
        raise NotImplementedError
    
    def delete(self, remote_path: str) -> bool:
        raise NotImplementedError
