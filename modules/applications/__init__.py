"""Application Tracking System (ADR-004).

SQLite/GCS-backed tracking for 190+ job applications.
CI-triggered pipeline, no permanent server.
"""

from .models import Application, CrawlResult, ApplicationHistory, Base
from .database import (
    get_engine,
    get_session,
    init_db,
    download_db,
    upload_db,
    gcs_managed_db,
)

__all__ = [
    "Application",
    "CrawlResult",
    "ApplicationHistory",
    "Base",
    "get_engine",
    "get_session",
    "init_db",
    "download_db",
    "upload_db",
    "gcs_managed_db",
]
