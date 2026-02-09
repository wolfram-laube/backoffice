"""Database engine, session management, and GCS state persistence.

Pattern follows runner_bandit GCSBackend:
  1. Download SQLite from GCS (if exists)
  2. Work locally
  3. Upload back to GCS

Environment variables:
  APPTRACK_GCS_BUCKET  — GCS bucket name (default: blauweiss-apptrack)
  APPTRACK_GCS_BLOB    — Blob path (default: applications.db)
  APPTRACK_DB_PATH     — Local SQLite path (default: /tmp/applications.db)
  GCP_SA_KEY           — Service account JSON (CI variable)
"""
import json
import logging
import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

logger = logging.getLogger(__name__)

# Defaults
DEFAULT_DB_PATH = "/tmp/applications.db"
DEFAULT_GCS_BUCKET = "blauweiss-apptrack"
DEFAULT_GCS_BLOB = "applications.db"


def get_db_path() -> Path:
    """Local SQLite file path."""
    return Path(os.getenv("APPTRACK_DB_PATH", DEFAULT_DB_PATH))


def get_engine(db_path: Optional[Path] = None, echo: bool = False):
    """Create SQLAlchemy engine for local SQLite file."""
    path = db_path or get_db_path()
    url = f"sqlite:///{path}"
    engine = create_engine(url, echo=echo)

    # Enable WAL mode and foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def get_session_factory(engine=None) -> sessionmaker:
    """Create a session factory."""
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_session(engine=None) -> Generator[Session, None, None]:
    """Context manager for database sessions with auto-commit/rollback."""
    factory = get_session_factory(engine)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine=None) -> None:
    """Create all tables (for initial setup or testing)."""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)
    logger.info("Database tables created.")


# ---------------------------------------------------------------------------
# GCS State Management
# ---------------------------------------------------------------------------

def _get_gcs_client():
    """Get authenticated GCS client.

    Priority:
      1. GCP_SA_KEY env var (CI pipeline — JSON string)
      2. GOOGLE_APPLICATION_CREDENTIALS file (local dev)
      3. Default credentials (GCE metadata, etc.)
    """
    from google.cloud import storage

    sa_key = os.getenv("GCP_SA_KEY") or os.getenv("GCP_SERVICE_ACCOUNT_KEY")
    if sa_key:
        import tempfile
        # Write SA key to temp file for client
        key_data = json.loads(sa_key)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(key_data, f)
            key_path = f.name
        client = storage.Client.from_service_account_json(key_path)
        os.unlink(key_path)
        return client

    return storage.Client()


def download_db(
    bucket_name: Optional[str] = None,
    blob_name: Optional[str] = None,
    local_path: Optional[Path] = None,
) -> Path:
    """Download SQLite database from GCS.

    Returns local path. If blob doesn't exist, returns path (file won't exist).
    """
    bucket_name = bucket_name or os.getenv("APPTRACK_GCS_BUCKET", DEFAULT_GCS_BUCKET)
    blob_name = blob_name or os.getenv("APPTRACK_GCS_BLOB", DEFAULT_GCS_BLOB)
    local_path = local_path or get_db_path()

    try:
        client = _get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        if blob.exists():
            local_path.parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(str(local_path))
            size_kb = local_path.stat().st_size / 1024
            logger.info(
                f"Downloaded gs://{bucket_name}/{blob_name} → {local_path} ({size_kb:.1f} KB)"
            )
        else:
            logger.info(
                f"No existing DB at gs://{bucket_name}/{blob_name} — starting fresh"
            )
    except Exception as e:
        logger.warning(f"GCS download failed: {e} — using local DB")

    return local_path


def upload_db(
    local_path: Optional[Path] = None,
    bucket_name: Optional[str] = None,
    blob_name: Optional[str] = None,
) -> bool:
    """Upload SQLite database to GCS.

    Returns True on success.
    """
    local_path = local_path or get_db_path()
    bucket_name = bucket_name or os.getenv("APPTRACK_GCS_BUCKET", DEFAULT_GCS_BUCKET)
    blob_name = blob_name or os.getenv("APPTRACK_GCS_BLOB", DEFAULT_GCS_BLOB)

    if not local_path.exists():
        logger.error(f"Local DB not found: {local_path}")
        return False

    try:
        client = _get_gcs_client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)

        # Upload with checksum for integrity
        blob.upload_from_filename(
            str(local_path),
            content_type="application/x-sqlite3",
        )
        size_kb = local_path.stat().st_size / 1024
        logger.info(
            f"Uploaded {local_path} → gs://{bucket_name}/{blob_name} ({size_kb:.1f} KB)"
        )
        return True

    except Exception as e:
        logger.error(f"GCS upload failed: {e}")
        return False


@contextmanager
def gcs_managed_db(
    bucket_name: Optional[str] = None,
    blob_name: Optional[str] = None,
):
    """Context manager: download DB from GCS, yield engine, upload back.

    Usage in CI:
        with gcs_managed_db() as engine:
            with get_session(engine) as session:
                # ... work with DB
    """
    local_path = download_db(bucket_name, blob_name)
    engine = get_engine(local_path)

    try:
        yield engine
    finally:
        engine.dispose()
        upload_db(local_path, bucket_name, blob_name)
