"""Storage abstraction layer for S3/GCS/GDrive."""

from .backend import StorageBackend
from .gdrive import GDriveStorage
from .s3 import S3Storage

__all__ = ['StorageBackend', 'GDriveStorage', 'S3Storage']
