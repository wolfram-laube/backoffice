"""Application Tracking System (ADR-004).

SQLite/GCS-backed tracking for 190+ job applications.
CI-triggered pipeline, no permanent server.

Sprint 1: CSV import/export, SQLAlchemy models
Sprint 2: Crawl integration (crawl → match → stage → CRM)
Sprint 3: Pages frontend dashboard
Sprint 4: Vorhölle review layer (pending_review → approve/dismiss)
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
from .review_service import (
    promote_to_review,
    approve_crawl_result,
    dismiss_crawl_result,
    get_review_queue,
    approve_all_above,
    get_review_summary,
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
    # Review layer (Sprint 4)
    "promote_to_review",
    "approve_crawl_result",
    "dismiss_crawl_result",
    "get_review_queue",
    "approve_all_above",
    "get_review_summary",
]
