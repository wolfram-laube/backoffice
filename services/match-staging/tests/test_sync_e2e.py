"""End-to-end tests for DB Sync (SQLite ↔ Storage Backend).

Tests the full persistence lifecycle:
1. Fresh start — no remote DB exists
2. Upload after writes
3. Download on startup (restore)
4. Integrity verification (MD5)
5. Skip upload when unchanged
6. Versioned backups
7. Backup rotation
8. WAL checkpoint before upload
9. Concurrent write → upload cycle
10. Full service lifecycle simulation
11. Backend abstraction contract

All tests use LocalBackend (same interface as GCSBackend).
"""

import csv
import os
import sqlite3
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select, func

from src.db.sync import DBSync, LocalBackend, StorageBackend


# --- Fixtures ---


@pytest.fixture
def storage_dir(tmp_path) -> Path:
    """Simulated remote storage directory."""
    d = tmp_path / "remote-gcs"
    d.mkdir()
    return d


@pytest.fixture
def backend(storage_dir) -> LocalBackend:
    return LocalBackend(base_dir=str(storage_dir))


@pytest.fixture
def db_dir(tmp_path) -> Path:
    """Local database directory."""
    d = tmp_path / "data"
    d.mkdir()
    return d


@pytest.fixture
def db_path(db_dir) -> Path:
    return db_dir / "bewerbungen.db"


@pytest.fixture
def sync(db_path, backend) -> DBSync:
    return DBSync(
        db_path=str(db_path),
        backend=backend,
        remote_key="bewerbungen.db",
        max_backups=3,
    )


def create_test_db(path: Path, n_rows: int = 5) -> Path:
    """Create a SQLite DB with test data."""
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY,
            project_title TEXT NOT NULL,
            provider TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'identified',
            match_score INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for i in range(n_rows):
        conn.execute(
            "INSERT INTO applications (project_title, provider, status, match_score) VALUES (?, ?, ?, ?)",
            (f"Project {i+1}", f"Provider {i+1}", "sent" if i % 2 else "identified", 70 + i * 5),
        )
    conn.commit()
    conn.close()
    return path


def count_rows(path: Path) -> int:
    """Count rows in the applications table."""
    conn = sqlite3.connect(str(path))
    count = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    conn.close()
    return count


def add_rows(path: Path, n: int = 1) -> None:
    """Add rows to an existing DB."""
    conn = sqlite3.connect(str(path))
    for i in range(n):
        conn.execute(
            "INSERT INTO applications (project_title, provider, status, match_score) VALUES (?, ?, ?, ?)",
            (f"New Project {i}", "New Provider", "staged", 95),
        )
    conn.commit()
    conn.close()


# ============================================================
# 1. FRESH START — no remote DB
# ============================================================


class TestFreshStart:
    @pytest.mark.asyncio
    async def test_download_when_no_remote(self, sync):
        """First startup with empty remote should return restored=False."""
        result = await sync.download()
        assert result["restored"] is False
        assert result["size"] == 0
        assert result["source"] is None

    @pytest.mark.asyncio
    async def test_fresh_db_then_upload(self, sync, db_path):
        """Create local DB, upload, verify remote exists."""
        create_test_db(db_path, n_rows=10)

        result = await sync.upload()
        assert result["uploaded"] is True
        assert result["size"] > 0
        assert result["md5"] is not None
        assert result["backup_key"] is None  # No backup on first upload

    @pytest.mark.asyncio
    async def test_upload_creates_remote_file(self, sync, db_path, backend):
        """After upload, remote file should exist."""
        create_test_db(db_path)
        await sync.upload()

        assert await backend.exists("bewerbungen.db")
        meta = await backend.get_metadata("bewerbungen.db")
        assert meta is not None
        assert meta["size"] > 0


# ============================================================
# 2. UPLOAD AFTER WRITES
# ============================================================


class TestUploadAfterWrites:
    @pytest.mark.asyncio
    async def test_upload_reflects_new_data(self, sync, db_path, db_dir, backend):
        """Upload after adding rows should persist new data."""
        create_test_db(db_path, n_rows=5)
        await sync.upload()

        # Add rows
        add_rows(db_path, n=3)
        assert count_rows(db_path) == 8

        # Upload again
        result = await sync.upload()
        assert result["uploaded"] is True

        # Verify by downloading to fresh location
        fresh = db_dir / "verify.db"
        await backend.download("bewerbungen.db", str(fresh))
        assert count_rows(fresh) == 8

    @pytest.mark.asyncio
    async def test_upload_without_local_db(self, sync):
        """Upload when no local DB exists should return uploaded=False."""
        result = await sync.upload()
        assert result["uploaded"] is False


# ============================================================
# 3. DOWNLOAD ON STARTUP (restore)
# ============================================================


class TestDownloadRestore:
    @pytest.mark.asyncio
    async def test_restore_from_remote(self, sync, db_path, backend, db_dir):
        """Should restore DB from remote on startup."""
        # Simulate a previous session: create DB, upload, delete local
        create_test_db(db_path, n_rows=10)
        await sync.upload()
        db_path.unlink()
        assert not db_path.exists()

        # New session: download
        result = await sync.download()
        assert result["restored"] is True
        assert result["size"] > 0
        assert db_path.exists()
        assert count_rows(db_path) == 10

    @pytest.mark.asyncio
    async def test_restore_preserves_all_data(self, sync, db_path, backend):
        """Restored DB should have identical data."""
        create_test_db(db_path, n_rows=20)

        # Record original data
        conn = sqlite3.connect(str(db_path))
        original_data = conn.execute(
            "SELECT project_title, provider, status, match_score FROM applications ORDER BY id"
        ).fetchall()
        conn.close()

        # Upload, delete, restore
        await sync.upload()
        db_path.unlink()
        await sync.download()

        # Compare
        conn = sqlite3.connect(str(db_path))
        restored_data = conn.execute(
            "SELECT project_title, provider, status, match_score FROM applications ORDER BY id"
        ).fetchall()
        conn.close()

        assert original_data == restored_data


# ============================================================
# 4. INTEGRITY VERIFICATION (MD5)
# ============================================================


class TestIntegrity:
    @pytest.mark.asyncio
    async def test_verify_matches_after_upload(self, sync, db_path):
        """MD5 should match immediately after upload."""
        create_test_db(db_path)
        await sync.upload()

        result = await sync.verify()
        assert result["match"] is True
        assert result["local_md5"] == result["remote_md5"]
        assert result["local_md5"] is not None

    @pytest.mark.asyncio
    async def test_verify_mismatch_after_local_write(self, sync, db_path):
        """MD5 should mismatch after local changes without re-upload."""
        create_test_db(db_path, n_rows=5)
        await sync.upload()

        # Modify local
        add_rows(db_path, n=3)

        result = await sync.verify()
        assert result["match"] is False
        assert result["local_md5"] != result["remote_md5"]

    @pytest.mark.asyncio
    async def test_verify_no_local_db(self, sync):
        """Verify with no local DB should return match=False."""
        result = await sync.verify()
        assert result["match"] is False
        assert result["local_md5"] is None


# ============================================================
# 5. SKIP UPLOAD WHEN UNCHANGED
# ============================================================


class TestSkipUnchanged:
    @pytest.mark.asyncio
    async def test_skip_when_identical(self, sync, db_path):
        """Should skip upload if local MD5 matches remote."""
        create_test_db(db_path)
        first = await sync.upload()
        assert first["uploaded"] is True

        # Upload again without changes
        second = await sync.upload()
        assert second.get("skipped") is True
        assert second["uploaded"] is False
        assert second["md5"] == first["md5"]

    @pytest.mark.asyncio
    async def test_upload_after_skip_when_changed(self, sync, db_path):
        """Should upload after a skip if data changes."""
        create_test_db(db_path)
        await sync.upload()

        # No change → skip
        result = await sync.upload()
        assert result.get("skipped") is True

        # Change → upload
        add_rows(db_path)
        result = await sync.upload()
        assert result["uploaded"] is True
        assert result.get("skipped") is not True


# ============================================================
# 6. VERSIONED BACKUPS
# ============================================================


class TestVersionedBackups:
    @pytest.mark.asyncio
    async def test_backup_created_on_second_upload(self, sync, db_path, backend):
        """Second upload should create a versioned backup."""
        create_test_db(db_path, n_rows=5)
        first = await sync.upload()
        assert first["backup_key"] is None  # First upload — no prior remote

        # Modify and upload again
        add_rows(db_path, n=3)
        second = await sync.upload()
        assert second["backup_key"] is not None
        assert "backups/" in second["backup_key"]

        # Verify backup exists and has old data
        assert await backend.exists(second["backup_key"])

    @pytest.mark.asyncio
    async def test_backup_contains_previous_version(self, sync, db_path, backend, db_dir):
        """Backup should contain the data from before the update."""
        create_test_db(db_path, n_rows=5)
        await sync.upload()

        # Modify and upload
        add_rows(db_path, n=10)
        result = await sync.upload()

        # Download backup — should have 5 rows, not 15
        backup_path = db_dir / "backup.db"
        await backend.download(result["backup_key"], str(backup_path))
        assert count_rows(backup_path) == 5

    @pytest.mark.asyncio
    async def test_multiple_backups(self, sync, db_path, backend):
        """Multiple uploads should create multiple backups."""
        create_test_db(db_path, n_rows=1)
        await sync.upload()

        backup_keys = []
        for i in range(3):
            add_rows(db_path, n=1)
            result = await sync.upload()
            if result.get("backup_key"):
                backup_keys.append(result["backup_key"])

        assert len(backup_keys) == 3
        # All should exist
        for key in backup_keys:
            assert await backend.exists(key)


# ============================================================
# 7. BACKUP ROTATION
# ============================================================


class TestBackupRotation:
    @pytest.mark.asyncio
    async def test_rotation_respects_max_backups(self, sync, db_path, backend):
        """Should keep at most max_backups (3) versions."""
        sync.max_backups = 3

        create_test_db(db_path, n_rows=1)
        await sync.upload()

        # Create 6 backups (exceeding max_backups=3)
        for i in range(6):
            add_rows(db_path, n=1)
            await sync.upload()

        # List backups
        versions = await backend.list_versions("backups/bewerbungen.db")
        assert len(versions) <= 3

    @pytest.mark.asyncio
    async def test_rotation_keeps_newest(self, sync, db_path, backend, db_dir):
        """Rotation should keep the newest backups."""
        sync.max_backups = 2

        create_test_db(db_path, n_rows=1)
        await sync.upload()

        # Create several versions with distinct data
        for i in range(4):
            add_rows(db_path, n=1)
            await sync.upload()

        # The surviving backups should have the most rows
        versions = await backend.list_versions("backups/bewerbungen.db")
        for v in versions:
            vpath = db_dir / f"check_{v['remote_key'].replace('/', '_')}"
            await backend.download(v["remote_key"], str(vpath))
            rows = count_rows(vpath)
            # Recent backups should have more rows than the initial 1
            assert rows >= 2


# ============================================================
# 8. WAL CHECKPOINT
# ============================================================


class TestWALCheckpoint:
    @pytest.mark.asyncio
    async def test_wal_merged_before_upload(self, sync, db_path):
        """WAL file should be merged into main DB before upload."""
        create_test_db(db_path, n_rows=5)

        # Force some WAL activity
        add_rows(db_path, n=3)

        wal_path = Path(f"{db_path}-wal")
        # WAL might exist after writes
        # (sometimes SQLite auto-checkpoints, so we can't guarantee it exists)

        # Upload triggers checkpoint
        await sync.upload()

        # After upload, WAL should be gone or empty
        if wal_path.exists():
            assert wal_path.stat().st_size == 0

    @pytest.mark.asyncio
    async def test_uploaded_db_is_self_contained(self, sync, db_path, backend, db_dir):
        """Downloaded DB should work without any WAL file."""
        create_test_db(db_path, n_rows=10)
        add_rows(db_path, n=5)  # Creates WAL activity
        await sync.upload()

        # Download to new location (no WAL/SHM)
        fresh = db_dir / "fresh.db"
        await backend.download("bewerbungen.db", str(fresh))

        # Should not have WAL/SHM companions
        assert not Path(f"{fresh}-wal").exists()
        assert not Path(f"{fresh}-shm").exists()

        # Should still have all data
        assert count_rows(fresh) == 15


# ============================================================
# 9. MULTIPLE WRITE→UPLOAD CYCLES
# ============================================================


class TestWriteUploadCycles:
    @pytest.mark.asyncio
    async def test_repeated_cycles(self, sync, db_path, backend, db_dir):
        """Simulate multiple session cycles: write → upload → (restart) → download → write → upload."""
        # Cycle 1: Create and upload
        create_test_db(db_path, n_rows=5)
        await sync.upload()
        assert count_rows(db_path) == 5

        # Cycle 2: Simulate restart — delete local, restore, add, upload
        db_path.unlink()
        for p in db_path.parent.glob(f"{db_path.name}*"):
            p.unlink()

        await sync.download()
        assert count_rows(db_path) == 5

        add_rows(db_path, n=3)
        await sync.upload()

        # Cycle 3: Another restart
        db_path.unlink()
        for p in db_path.parent.glob(f"{db_path.name}*"):
            p.unlink()

        await sync.download()
        assert count_rows(db_path) == 8

        # Cycle 4: Add more, upload, verify
        add_rows(db_path, n=2)
        await sync.upload()

        verify = await sync.verify()
        assert verify["match"] is True

        # Independent download verification
        check_path = db_dir / "final_check.db"
        await backend.download("bewerbungen.db", str(check_path))
        assert count_rows(check_path) == 10

    @pytest.mark.asyncio
    async def test_upload_count_tracked(self, sync, db_path):
        """Stats should track upload count."""
        create_test_db(db_path)

        assert sync.stats["upload_count"] == 0
        await sync.upload()
        assert sync.stats["upload_count"] == 1

        add_rows(db_path)
        await sync.upload()
        assert sync.stats["upload_count"] == 2

        # Skipped upload shouldn't increment
        await sync.upload()  # No changes → skip
        assert sync.stats["upload_count"] == 2


# ============================================================
# 10. FULL SERVICE LIFECYCLE SIMULATION
# ============================================================


class TestFullLifecycle:
    @pytest.mark.asyncio
    async def test_complete_service_lifecycle(self, db_dir, backend):
        """Simulate a complete match-staging service lifecycle:

        Session 1: Fresh start, migrate CSV, create matches, upload
        Session 2: Restore, add more matches, update statuses, upload
        Session 3: Restore, verify all data intact
        """
        db_file = db_dir / "lifecycle.db"

        # === SESSION 1: Fresh start ===
        sync1 = DBSync(str(db_file), backend, remote_key="lifecycle.db")

        # No remote DB yet
        restore = await sync1.download()
        assert restore["restored"] is False

        # Create schema and seed data (simulating CSV migration)
        conn = sqlite3.connect(str(db_file))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE applications (
                id INTEGER PRIMARY KEY,
                project_title TEXT NOT NULL,
                provider TEXT NOT NULL,
                status TEXT NOT NULL,
                match_score INTEGER,
                draft_text TEXT,
                gitlab_issue_iid INTEGER,
                notes TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE status_history (
                id INTEGER PRIMARY KEY,
                application_id INTEGER REFERENCES applications(id),
                old_status TEXT,
                new_status TEXT NOT NULL,
                changed_by TEXT,
                changed_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Import 3 applications
        apps = [
            ("Cloud Architect - Multi-Cloud", "Amoria Bond", "identified", 97, None, None),
            ("DevOps Engineer K8s", "Nemensis", "sent", 85, "Sehr geehrte...", 49),
            ("SRE Agent KI", "SThree", "identified", 92, None, None),
        ]
        for title, prov, status, score, draft, iid in apps:
            conn.execute(
                "INSERT INTO applications (project_title, provider, status, match_score, draft_text, gitlab_issue_iid) VALUES (?,?,?,?,?,?)",
                (title, prov, status, score, draft, iid),
            )
        conn.commit()
        conn.close()

        # Upload
        up1 = await sync1.upload()
        assert up1["uploaded"] is True
        assert up1["size"] > 0

        # === SESSION 2: Restore + work ===
        db_file.unlink()  # Simulate container restart
        for p in db_dir.glob("lifecycle.db*"):
            p.unlink()

        sync2 = DBSync(str(db_file), backend, remote_key="lifecycle.db")
        restore2 = await sync2.download()
        assert restore2["restored"] is True

        conn = sqlite3.connect(str(db_file))

        # Verify data survived
        count = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        assert count == 3

        # Update status: approve the 97% match
        conn.execute(
            "UPDATE applications SET status='approved' WHERE match_score=97"
        )
        conn.execute(
            "INSERT INTO status_history (application_id, old_status, new_status, changed_by) VALUES (1, 'identified', 'approved', 'user')"
        )

        # Add a new match
        conn.execute(
            "INSERT INTO applications (project_title, provider, status, match_score) VALUES (?, ?, ?, ?)",
            ("Platform Engineer Azure", "GULP", "staged", 88),
        )
        conn.commit()
        conn.close()

        up2 = await sync2.upload()
        assert up2["uploaded"] is True
        assert up2["backup_key"] is not None  # Should backup Session 1 state

        # === SESSION 3: Final restore + verify ===
        db_file.unlink()
        for p in db_dir.glob("lifecycle.db*"):
            p.unlink()

        sync3 = DBSync(str(db_file), backend, remote_key="lifecycle.db")
        restore3 = await sync3.download()
        assert restore3["restored"] is True

        conn = sqlite3.connect(str(db_file))

        # All 4 applications present
        total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        assert total == 4

        # Status updated correctly
        approved = conn.execute(
            "SELECT project_title FROM applications WHERE status='approved'"
        ).fetchone()
        assert "Cloud Architect" in approved[0]

        # History preserved
        history = conn.execute("SELECT * FROM status_history").fetchall()
        assert len(history) == 1
        assert history[0][3] == "approved"  # new_status
        assert history[0][4] == "user"  # changed_by

        # New match present
        gulp = conn.execute(
            "SELECT match_score FROM applications WHERE provider='GULP'"
        ).fetchone()
        assert gulp[0] == 88

        conn.close()

        # Final verify
        verify = await sync3.verify()
        assert verify["match"] is True


# ============================================================
# 11. BACKEND ABSTRACTION CONTRACT
# ============================================================


class TestBackendContract:
    """Verify LocalBackend satisfies the StorageBackend interface."""

    @pytest.mark.asyncio
    async def test_is_storage_backend(self, backend):
        assert isinstance(backend, StorageBackend)

    @pytest.mark.asyncio
    async def test_upload_returns_metadata(self, backend, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")

        meta = await backend.upload(str(test_file), "test.txt")
        assert "size" in meta
        assert "md5" in meta
        assert "uploaded_at" in meta
        assert "remote_key" in meta
        assert meta["size"] == 5

    @pytest.mark.asyncio
    async def test_download_nonexistent(self, backend, tmp_path):
        result = await backend.download("nonexistent.db", str(tmp_path / "out.db"))
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_contract(self, backend, tmp_path):
        assert await backend.exists("nope.db") is False

        f = tmp_path / "yes.txt"
        f.write_text("data")
        await backend.upload(str(f), "yes.txt")
        assert await backend.exists("yes.txt") is True

    @pytest.mark.asyncio
    async def test_delete_contract(self, backend, tmp_path):
        f = tmp_path / "del.txt"
        f.write_text("bye")
        await backend.upload(str(f), "del.txt")

        assert await backend.delete("del.txt") is True
        assert await backend.exists("del.txt") is False
        assert await backend.delete("del.txt") is False  # Already gone

    @pytest.mark.asyncio
    async def test_metadata_contract(self, backend, tmp_path):
        assert await backend.get_metadata("nope") is None

        f = tmp_path / "meta.txt"
        f.write_text("metadata test content")
        await backend.upload(str(f), "meta.txt")

        meta = await backend.get_metadata("meta.txt")
        assert meta is not None
        assert meta["size"] == len("metadata test content")
        assert "md5" in meta
        assert "updated_at" in meta

    @pytest.mark.asyncio
    async def test_list_versions_contract(self, backend, tmp_path):
        # Upload several versioned files
        for i in range(3):
            f = tmp_path / f"v{i}.txt"
            f.write_text(f"version {i}")
            await backend.upload(str(f), f"backups/data_v{i}.db")

        versions = await backend.list_versions("backups/data_v0.db")
        assert len(versions) >= 1  # At least the ones matching the prefix
