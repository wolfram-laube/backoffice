"""Google Drive storage backend."""
from pathlib import Path
from typing import List
from .backend import StorageBackend


class GDriveStorage(StorageBackend):
    """Google Drive storage using rclone or API."""
    
    def __init__(self, remote_name: str = 'gdrive', base_path: str = ''):
        self.remote_name = remote_name
        self.base_path = base_path
    
    def upload(self, local_path: Path, remote_path: str) -> str:
        # TODO: Implement with rclone or google-api-python-client
        raise NotImplementedError
    
    def download(self, remote_path: str, local_path: Path) -> Path:
        raise NotImplementedError
    
    def list(self, prefix: str = '') -> List[str]:
        raise NotImplementedError
    
    def delete(self, remote_path: str) -> bool:
        raise NotImplementedError
