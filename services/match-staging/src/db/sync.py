"""Storage backend for SQLite database persistence.

Provides a clean abstraction over:
- GCS (Google Cloud Storage) — production
- Local filesystem — testing & development

Usage:
    backend = GCSBackend(bucket="blauweiss-ops", prefix="match-staging")
    # or
    backend = LocalBackend(base_dir="/tmp/db-sync")

    sync = DBSync(db_path="data/bewerbungen.db", backend=backend)
    await sync.download()   # Restore DB from remote on startup
    await sync.upload()     # Persist DB to remote after writes
"""

import hashlib
import os
import shutil
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import logging

logger = logging.getLogger(__name__)


# ============================================================
# Backend Protocol
# ============================================================


class StorageBackend(ABC):
    """Abstract storage backend for DB file persistence."""

    @abstractmethod
    async def upload(self, local_path: str, remote_key: str) -> dict:
        """Upload a file to remote storage.

        Returns:
            Metadata dict: {size, md5, uploaded_at, remote_key}
        """
        ...

    @abstractmethod
    async def download(self, remote_key: str, local_path: str) -> bool:
        """Download a file from remote storage.

        Returns:
            True if file was downloaded, False if not found.
        """
        ...

    @abstractmethod
    async def exists(self, remote_key: str) -> bool:
        """Check if a remote file exists."""
        ...

    @abstractmethod
    async def get_metadata(self, remote_key: str) -> Optional[dict]:
        """Get metadata for a remote file.

        Returns:
            {size, md5, updated_at} or None if not found.
        """
        ...

    @abstractmethod
    async def list_versions(self, remote_key: str, max_results: int = 10) -> list[dict]:
        """List available versions/backups of a file.

        Returns:
            List of {remote_key, size, updated_at}
        """
        ...

    @abstractmethod
    async def delete(self, remote_key: str) -> bool:
        """Delete a remote file. Returns True if deleted."""
        ...


# ============================================================
# Local Filesystem Backend (testing & dev)
# ============================================================


class LocalBackend(StorageBackend):
    """Filesystem-based storage backend for testing.

    Mimics GCS behavior using a local directory.
    """

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, remote_key: str) -> Path:
        return self.base_dir / remote_key

    @staticmethod
    def _md5(path: Path) -> str:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    async def upload(self, local_path: str, remote_key: str) -> dict:
        src = Path(local_path)
        dst = self._resolve(remote_key)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))

        meta = {
            "size": dst.stat().st_size,
            "md5": self._md5(dst),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "remote_key": remote_key,
        }
        logger.info(f"LocalBackend: uploaded {local_path} → {remote_key} ({meta['size']} bytes)")
        return meta

    async def download(self, remote_key: str, local_path: str) -> bool:
        src = self._resolve(remote_key)
        if not src.exists():
            logger.warning(f"LocalBackend: {remote_key} not found")
            return False

        dst = Path(local_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst))
        logger.info(f"LocalBackend: downloaded {remote_key} → {local_path}")
        return True

    async def exists(self, remote_key: str) -> bool:
        return self._resolve(remote_key).exists()

    async def get_metadata(self, remote_key: str) -> Optional[dict]:
        path = self._resolve(remote_key)
        if not path.exists():
            return None
        return {
            "size": path.stat().st_size,
            "md5": self._md5(path),
            "updated_at": datetime.fromtimestamp(
                path.stat().st_mtime, tz=timezone.utc
            ).isoformat(),
        }

    async def list_versions(self, remote_key: str, max_results: int = 10) -> list[dict]:
        """List versioned backups matching the key prefix."""
        parent = self._resolve(remote_key).parent
        stem = Path(remote_key).stem
        suffix = Path(remote_key).suffix

        versions = []
        if parent.exists():
            for f in sorted(parent.iterdir(), reverse=True):
                if f.name.startswith(stem) and f.suffix == suffix:
                    versions.append({
                        "remote_key": str(f.relative_to(self.base_dir)),
                        "size": f.stat().st_size,
                        "updated_at": datetime.fromtimestamp(
                            f.stat().st_mtime, tz=timezone.utc
                        ).isoformat(),
                    })
                if len(versions) >= max_results:
                    break
        return versions

    async def delete(self, remote_key: str) -> bool:
        path = self._resolve(remote_key)
        if path.exists():
            path.unlink()
            return True
        return False


# ============================================================
# GCS Backend (production)
# ============================================================


class GCSBackend(StorageBackend):
    """Google Cloud Storage backend.

    Requires:
        pip install google-cloud-storage
        GOOGLE_APPLICATION_CREDENTIALS env var or Application Default Credentials
    """

    def __init__(self, bucket: str, prefix: str = ""):
        self.bucket_name = bucket
        self.prefix = prefix.strip("/")
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google.cloud import storage
            self._client = storage.Client()
        return self._client

    def _get_bucket(self):
        return self._get_client().bucket(self.bucket_name)

    def _full_key(self, remote_key: str) -> str:
        if self.prefix:
            return f"{self.prefix}/{remote_key}"
        return remote_key

    async def upload(self, local_path: str, remote_key: str) -> dict:
        import asyncio
        loop = asyncio.get_event_loop()

        def _upload():
            blob = self._get_bucket().blob(self._full_key(remote_key))
            blob.upload_from_filename(local_path)
            blob.reload()
            return {
                "size": blob.size,
                "md5": blob.md5_hash,
                "uploaded_at": blob.updated.isoformat() if blob.updated else None,
                "remote_key": remote_key,
            }

        meta = await loop.run_in_executor(None, _upload)
        logger.info(f"GCS: uploaded {local_path} → gs://{self.bucket_name}/{self._full_key(remote_key)}")
        return meta

    async def download(self, remote_key: str, local_path: str) -> bool:
        import asyncio
        loop = asyncio.get_event_loop()

        def _download():
            blob = self._get_bucket().blob(self._full_key(remote_key))
            if not blob.exists():
                return False
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            blob.download_to_filename(local_path)
            return True

        found = await loop.run_in_executor(None, _download)
        if found:
            logger.info(f"GCS: downloaded gs://{self.bucket_name}/{self._full_key(remote_key)} → {local_path}")
        return found

    async def exists(self, remote_key: str) -> bool:
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self._get_bucket().blob(self._full_key(remote_key)).exists()
        )

    async def get_metadata(self, remote_key: str) -> Optional[dict]:
        import asyncio
        loop = asyncio.get_event_loop()

        def _meta():
            blob = self._get_bucket().blob(self._full_key(remote_key))
            if not blob.exists():
                return None
            blob.reload()
            return {
                "size": blob.size,
                "md5": blob.md5_hash,
                "updated_at": blob.updated.isoformat() if blob.updated else None,
            }

        return await loop.run_in_executor(None, _meta)

    async def list_versions(self, remote_key: str, max_results: int = 10) -> list[dict]:
        import asyncio
        loop = asyncio.get_event_loop()

        def _list():
            prefix = self._full_key(remote_key).rsplit(".", 1)[0]
            blobs = self._get_client().list_blobs(
                self.bucket_name, prefix=prefix, max_results=max_results
            )
            return [
                {
                    "remote_key": b.name.removeprefix(f"{self.prefix}/") if self.prefix else b.name,
                    "size": b.size,
                    "updated_at": b.updated.isoformat() if b.updated else None,
                }
                for b in blobs
            ]

        return await loop.run_in_executor(None, _list)

    async def delete(self, remote_key: str) -> bool:
        import asyncio
        loop = asyncio.get_event_loop()

        def _delete():
            blob = self._get_bucket().blob(self._full_key(remote_key))
            if blob.exists():
                blob.delete()
                return True
            return False

        return await loop.run_in_executor(None, _delete)


# ============================================================
# DB Sync Orchestrator
# ============================================================


class DBSync:
    """Orchestrates SQLite database persistence via a storage backend.

    Handles:
    - Download on service startup (restore from remote)
    - Upload after writes (persist to remote)
    - Versioned backups with rotation
    - Integrity checks (MD5 comparison)
    - WAL checkpoint before upload (ensures consistency)
    """

    def __init__(
        self,
        db_path: str,
        backend: StorageBackend,
        remote_key: str = "bewerbungen.db",
        max_backups: int = 5,
    ):
        self.db_path = Path(db_path)
        self.backend = backend
        self.remote_key = remote_key
        self.max_backups = max_backups
        self._upload_count = 0

    @staticmethod
    def _local_md5(path: Path) -> str:
        h = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _checkpoint_wal(self) -> None:
        """Force WAL checkpoint to merge WAL into main DB file.

        Critical before upload — otherwise remote DB may be incomplete.
        """
        import sqlite3
        if not self.db_path.exists():
            return
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
        logger.info("WAL checkpoint completed")

        # Clean up WAL/SHM files if empty
        for suffix in ("-wal", "-shm"):
            wal = Path(f"{self.db_path}{suffix}")
            if wal.exists() and wal.stat().st_size == 0:
                wal.unlink()

    async def download(self) -> dict:
        """Download DB from remote storage on startup.

        Returns:
            {restored: bool, size: int, source: str}
        """
        if await self.backend.exists(self.remote_key):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            success = await self.backend.download(self.remote_key, str(self.db_path))
            if success:
                meta = await self.backend.get_metadata(self.remote_key)
                size = meta["size"] if meta else self.db_path.stat().st_size
                logger.info(f"DB restored from remote: {size} bytes")
                return {"restored": True, "size": size, "source": self.remote_key}

        logger.info("No remote DB found — starting fresh")
        return {"restored": False, "size": 0, "source": None}

    async def upload(self, create_backup: bool = True) -> dict:
        """Upload DB to remote storage after writes.

        Args:
            create_backup: If True, save a versioned backup before overwriting.

        Returns:
            {uploaded: bool, size: int, md5: str, backup_key: str|None}
        """
        if not self.db_path.exists():
            logger.warning("No local DB to upload")
            return {"uploaded": False, "size": 0, "md5": None, "backup_key": None}

        # Checkpoint WAL first
        self._checkpoint_wal()

        local_md5 = self._local_md5(self.db_path)

        # Check if remote is already up-to-date
        remote_meta = await self.backend.get_metadata(self.remote_key)
        if remote_meta and remote_meta.get("md5") == local_md5:
            logger.info("Remote DB already up-to-date, skipping upload")
            return {
                "uploaded": False,
                "size": self.db_path.stat().st_size,
                "md5": local_md5,
                "backup_key": None,
                "skipped": True,
            }

        # Create versioned backup
        backup_key = None
        if create_backup and remote_meta:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            stem = Path(self.remote_key).stem
            suffix = Path(self.remote_key).suffix
            backup_key = f"backups/{stem}_{ts}{suffix}"
            # Copy current remote to backup
            if await self.backend.exists(self.remote_key):
                # Download current, re-upload as backup
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp_path = tmp.name
                try:
                    await self.backend.download(self.remote_key, tmp_path)
                    await self.backend.upload(tmp_path, backup_key)
                    logger.info(f"Backup created: {backup_key}")
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

            # Rotate old backups
            await self._rotate_backups()

        # Upload current DB
        meta = await self.backend.upload(str(self.db_path), self.remote_key)
        self._upload_count += 1

        return {
            "uploaded": True,
            "size": meta["size"],
            "md5": local_md5,
            "backup_key": backup_key,
        }

    async def _rotate_backups(self) -> int:
        """Delete old backups beyond max_backups limit.

        Returns:
            Number of backups deleted.
        """
        stem = Path(self.remote_key).stem
        suffix = Path(self.remote_key).suffix
        versions = await self.backend.list_versions(f"backups/{stem}{suffix}")

        deleted = 0
        if len(versions) > self.max_backups:
            # Sort by updated_at desc, delete oldest
            versions.sort(key=lambda v: v.get("updated_at", ""), reverse=True)
            for old in versions[self.max_backups:]:
                await self.backend.delete(old["remote_key"])
                deleted += 1
                logger.info(f"Rotated old backup: {old['remote_key']}")

        return deleted

    async def verify(self) -> dict:
        """Verify local DB matches remote.

        Returns:
            {match: bool, local_md5: str, remote_md5: str}
        """
        if not self.db_path.exists():
            return {"match": False, "local_md5": None, "remote_md5": None}

        self._checkpoint_wal()
        local_md5 = self._local_md5(self.db_path)
        remote_meta = await self.backend.get_metadata(self.remote_key)

        remote_md5 = remote_meta.get("md5") if remote_meta else None
        return {
            "match": local_md5 == remote_md5,
            "local_md5": local_md5,
            "remote_md5": remote_md5,
        }

    @property
    def stats(self) -> dict:
        """Return sync statistics."""
        return {
            "db_path": str(self.db_path),
            "remote_key": self.remote_key,
            "upload_count": self._upload_count,
            "db_exists": self.db_path.exists(),
            "db_size": self.db_path.stat().st_size if self.db_path.exists() else 0,
        }
