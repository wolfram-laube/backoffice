"""Abstract storage backend."""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def upload(self, local_path: Path, remote_path: str) -> str:
        """Upload file, return remote URL."""
        pass
    
    @abstractmethod
    def download(self, remote_path: str, local_path: Path) -> Path:
        """Download file, return local path."""
        pass
    
    @abstractmethod
    def list(self, prefix: str = '') -> List[str]:
        """List files with optional prefix."""
        pass
    
    @abstractmethod
    def delete(self, remote_path: str) -> bool:
        """Delete file, return success."""
        pass
