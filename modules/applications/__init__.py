"""Application Tracking System (ADR-004).

SQLite/GCS-backed tracking for 190+ job applications.
CI-triggered pipeline, no permanent server.

Sprint 1: CSV import/export, SQLAlchemy models
Sprint 2: Crawl integration (crawl → match → stage → CRM)
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
from .crawl_service import (
    ingest_crawl_results,
    ingest_from_file,
    update_match_scores,
    update_matches_from_file,
    stage_to_application,
    stage_all_approved,
    sync_crm_labels,
    get_crm_label,
)

__all__ = [
    # Models
    "Application",
    "CrawlResult",
    "ApplicationHistory",
    "Base",
    # Database
    "get_engine",
    "get_session",
    "init_db",
    "download_db",
    "upload_db",
    "gcs_managed_db",
    # Crawl integration (Sprint 2)
    "ingest_crawl_results",
    "ingest_from_file",
    "update_match_scores",
    "update_matches_from_file",
    "stage_to_application",
    "stage_all_approved",
    "sync_crm_labels",
    "get_crm_label",
]
