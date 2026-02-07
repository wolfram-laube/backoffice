"""End-to-end tests for the Bewerbungen Database Pipeline.

Tests the full lifecycle:
1. Schema creation (fresh DB)
2. CSV migration (sample + real data)
3. CRUD operations
4. Status transitions + audit trail
5. Match cycle tracking
6. Query patterns (analytics, filtering, funnel)
7. GitLab issue linking
8. Data integrity constraints
9. CSV export roundtrip
10. Status normalizer unit tests
"""

import csv
import os
import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import select, func, text

# --- Test DB setup (before imports that use env) ---

_TEST_DB_DIR = tempfile.mkdtemp()


@pytest.fixture(autouse=True)
def _reset_db_singletons():
    """Reset DB singletons before each test."""
    import src.db.connection as conn_mod
    conn_mod._engine = None
    conn_mod._session_factory = None


@pytest_asyncio.fixture
async def fresh_db(tmp_path, _reset_db_singletons):
    """Create a fresh SQLite database for each test."""
    db_path = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"

    from src.db.connection import init_db, close_db
    await init_db()
    yield db_path
    await close_db()


@pytest.fixture
def sample_csv(tmp_path) -> Path:
    """Create a sample CSV matching the real schema."""
    csv_path = tmp_path / "test_bewerbungen.csv"
    rows = [
        {
            "date_recorded": "2026-02-08",
            "project_title": "Cloud Architect - Cloud-Transformation",
            "provider": "Amoria Bond GmbH",
            "contact_name": "Max Mustermann",
            "contact_email": "max@amoria.com",
            "phone": "+49 123 456",
            "location": "Heilbronn (100% Remote)",
            "start": "ASAP",
            "duration": "3 Monate + Uebernahme",
            "workload": "100%",
            "rate_eur_h": "105",
            "status": "neu identifiziert",
            "notes": "AWS/GCP, Kubernetes, Terraform. freelancermap",
        },
        {
            "date_recorded": "2026-01-15",
            "project_title": "DevOps Engineer K8s",
            "provider": "Nemensis AG",
            "contact_name": "",
            "contact_email": "",
            "phone": "",
            "location": "Frankfurt (75% Remote)",
            "start": "02.03.2026",
            "duration": "6 Monate",
            "workload": "FT",
            "rate_eur_h": "105",
            "status": "versendet (23.01.2026)",
            "notes": "Kubernetes, GitLab, ArgoCD",
        },
        {
            "date_recorded": "2025-11-10",
            "project_title": "Senior Platform Engineer",
            "provider": "GULP",
            "contact_name": "",
            "contact_email": "",
            "phone": "",
            "location": "Berlin",
            "start": "01.12.2025",
            "duration": "12 Monate",
            "workload": "100%",
            "rate_eur_h": "105",
            "status": "keine Rueckmeldung (versendet 2025-11-12)",
            "notes": "",
        },
        {
            "date_recorded": "2025-10-05",
            "project_title": "DevOps mit Copilot",
            "provider": "Akkodis",
            "contact_name": "",
            "contact_email": "",
            "phone": "",
            "location": "Remote",
            "start": "ASAP",
            "duration": "6 Mo",
            "workload": "100%",
            "rate_eur_h": "105",
            "status": "abgelehnt (07.11.2025)",
            "notes": "",
        },
        {
            "date_recorded": "2025-09-20",
            "project_title": "Rate-in-Status Bug",
            "provider": "Test Provider",
            "contact_name": "",
            "contact_email": "",
            "phone": "",
            "location": "Remote",
            "start": "ASAP",
            "duration": "6 Mo",
            "workload": "100%",
            "rate_eur_h": "",
            "status": "105",
            "notes": "This row has rate in the status field",
        },
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    return csv_path


# ============================================================
# 1. SCHEMA CREATION
# ============================================================


class TestSchemaCreation:
    @pytest.mark.asyncio
    async def test_tables_exist(self, fresh_db):
        import sqlite3
        db = sqlite3.connect(str(fresh_db))
        tables = [r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]
        db.close()

        assert "applications" in tables
        assert "status_history" in tables
        assert "match_cycles" in tables

    @pytest.mark.asyncio
    async def test_applications_has_all_columns(self, fresh_db):
        import sqlite3
        db = sqlite3.connect(str(fresh_db))
        cols = {r[1] for r in db.execute("PRAGMA table_info(applications)").fetchall()}
        db.close()

        expected = {
            "id", "date_recorded", "created_at", "updated_at",
            "project_title", "provider", "contact_name", "contact_email",
            "phone", "location", "start_date", "duration", "workload",
            "rate_eur_h", "remote_percentage", "source_platform", "source_url",
            "source_ref_id", "status", "status_date", "status_detail",
            "match_score", "match_tier", "match_breakdown", "strengths",
            "gaps", "draft_text", "draft_variant", "gitlab_issue_iid",
            "gitlab_issue_url", "notes",
        }
        missing = expected - cols
        assert not missing, f"Missing columns: {missing}"

    @pytest.mark.asyncio
    async def test_sqlite_wal_mode(self, fresh_db):
        import sqlite3
        db = sqlite3.connect(str(fresh_db))
        mode = db.execute("PRAGMA journal_mode").fetchone()[0]
        db.close()
        assert mode == "wal"

    @pytest.mark.asyncio
    async def test_idempotent_init(self, fresh_db):
        from src.db.connection import init_db, get_session
        from src.db.models import Application
        await init_db()  # Second call — should not error
        async with get_session() as session:
            count = await session.scalar(select(func.count(Application.id)))
            assert count == 0


# ============================================================
# 2. CSV MIGRATION
# ============================================================


class TestCSVMigration:
    @pytest.mark.asyncio
    async def test_imports_all_rows(self, fresh_db, sample_csv):
        from src.db.migrate_csv import migrate_csv
        stats = await migrate_csv(str(sample_csv))
        assert stats["total_rows"] == 5
        assert stats["imported"] == 5
        assert stats["skipped"] == 0
        assert stats["db_count"] == 5

    @pytest.mark.asyncio
    async def test_dry_run_writes_nothing(self, fresh_db, sample_csv):
        from src.db.migrate_csv import migrate_csv
        from src.db.connection import get_session
        from src.db.models import Application

        stats = await migrate_csv(str(sample_csv), dry_run=True)
        assert stats["imported"] == 5

        async with get_session() as session:
            count = await session.scalar(select(func.count(Application.id)))
            assert count == 0

    @pytest.mark.asyncio
    async def test_status_normalization(self, fresh_db, sample_csv):
        from src.db.migrate_csv import migrate_csv
        from src.db.connection import get_session
        from src.db.models import Application

        await migrate_csv(str(sample_csv))

        async with get_session() as session:
            apps = (await session.execute(
                select(Application).order_by(Application.date_recorded.desc())
            )).scalars().all()

        by_title = {a.project_title: a.status for a in apps}
        assert by_title["Cloud Architect - Cloud-Transformation"] == "identified"
        assert by_title["DevOps Engineer K8s"] == "sent"
        assert by_title["Senior Platform Engineer"] == "no_response"
        assert by_title["DevOps mit Copilot"] == "rejected"

    @pytest.mark.asyncio
    async def test_date_extraction_from_status(self, fresh_db, sample_csv):
        from src.db.migrate_csv import migrate_csv
        from src.db.connection import get_session
        from src.db.models import Application

        await migrate_csv(str(sample_csv))

        async with get_session() as session:
            app = (await session.execute(
                select(Application).where(Application.project_title == "DevOps Engineer K8s")
            )).scalar_one()

        assert app.status_date == date(2026, 1, 23)

    @pytest.mark.asyncio
    async def test_rate_in_status_repaired(self, fresh_db, sample_csv):
        from src.db.migrate_csv import migrate_csv
        from src.db.connection import get_session
        from src.db.models import Application

        await migrate_csv(str(sample_csv))

        async with get_session() as session:
            app = (await session.execute(
                select(Application).where(Application.project_title == "Rate-in-Status Bug")
            )).scalar_one()

        assert app.rate_eur_h == 105
        assert "rate_in_status_field" in (app.status_detail or "")

    @pytest.mark.asyncio
    async def test_platform_detection(self, fresh_db, sample_csv):
        from src.db.migrate_csv import migrate_csv
        from src.db.connection import get_session
        from src.db.models import Application

        await migrate_csv(str(sample_csv))

        async with get_session() as session:
            amoria = (await session.execute(
                select(Application).where(Application.project_title.contains("Cloud Architect"))
            )).scalar_one()
            gulp = (await session.execute(
                select(Application).where(Application.provider == "GULP")
            )).scalar_one()

        assert amoria.source_platform == "freelancermap"
        assert gulp.source_platform == "gulp"

    @pytest.mark.asyncio
    async def test_audit_trail_on_import(self, fresh_db, sample_csv):
        from src.db.migrate_csv import migrate_csv
        from src.db.connection import get_session
        from src.db.models import Application, StatusHistory

        await migrate_csv(str(sample_csv))

        async with get_session() as session:
            h_count = await session.scalar(select(func.count(StatusHistory.id)))
            a_count = await session.scalar(select(func.count(Application.id)))
            assert h_count == a_count  # 1:1

            h = (await session.execute(select(StatusHistory).limit(1))).scalar_one()
            assert h.changed_by == "csv_migration"
            assert h.old_status is None

    @pytest.mark.asyncio
    async def test_file_not_found(self, fresh_db):
        from src.db.migrate_csv import migrate_csv
        with pytest.raises(FileNotFoundError):
            await migrate_csv("/nonexistent.csv")


# ============================================================
# 3. CRUD OPERATIONS
# ============================================================


class TestCRUD:
    @pytest.mark.asyncio
    async def test_create_and_read(self, fresh_db):
        from src.db.connection import get_session
        from src.db.models import Application, ApplicationStatus, MatchTier

        async with get_session() as session:
            app = Application(
                date_recorded=date(2026, 2, 8),
                project_title="Test Cloud Architect",
                provider="Test GmbH",
                location="Remote",
                rate_eur_h=105,
                status=ApplicationStatus.IDENTIFIED.value,
                match_score=97,
                match_tier=MatchTier.HIGH.value,
            )
            session.add(app)

        async with get_session() as session:
            loaded = (await session.execute(
                select(Application).where(Application.project_title == "Test Cloud Architect")
            )).scalar_one()

        assert loaded.id is not None
        assert loaded.match_score == 97
        assert loaded.rate_eur_h == 105
        assert loaded.status == "identified"

    @pytest.mark.asyncio
    async def test_update(self, fresh_db):
        from src.db.connection import get_session
        from src.db.models import Application

        async with get_session() as session:
            app = Application(
                date_recorded=date.today(), project_title="Update Me",
                provider="P", status="identified",
            )
            session.add(app)
            await session.flush()
            app_id = app.id

        async with get_session() as session:
            app = await session.get(Application, app_id)
            app.status = "sent"
            app.match_score = 85

        async with get_session() as session:
            app = await session.get(Application, app_id)
            assert app.status == "sent"
            assert app.match_score == 85

    @pytest.mark.asyncio
    async def test_delete_cascades_history(self, fresh_db):
        from src.db.connection import get_session
        from src.db.models import Application, StatusHistory

        async with get_session() as session:
            app = Application(
                date_recorded=date.today(), project_title="Delete Me",
                provider="P", status="identified",
            )
            session.add(app)
            await session.flush()
            session.add(StatusHistory(
                application_id=app.id, new_status="identified", changed_by="test",
            ))
            app_id = app.id

        async with get_session() as session:
            app = await session.get(Application, app_id)
            await session.delete(app)

        async with get_session() as session:
            orphans = await session.scalar(
                select(func.count(StatusHistory.id)).where(
                    StatusHistory.application_id == app_id
                )
            )
            assert orphans == 0

    @pytest.mark.asyncio
    async def test_json_fields_roundtrip(self, fresh_db):
        from src.db.connection import get_session
        from src.db.models import Application

        breakdown = {
            "Cloud Architecture": {"score": 100, "note": "Multi-cloud"},
            "Kubernetes": {"score": 100, "note": "CKA/CKAD"},
        }
        strengths = ["Multi-cloud", "KRITIS"]
        gaps = ["Short duration"]

        async with get_session() as session:
            app = Application(
                date_recorded=date.today(), project_title="JSON Test",
                provider="P", status="identified",
                match_breakdown=breakdown, strengths=strengths, gaps=gaps,
            )
            session.add(app)
            await session.flush()
            app_id = app.id

        async with get_session() as session:
            app = await session.get(Application, app_id)
            assert app.match_breakdown["Kubernetes"]["score"] == 100
            assert "KRITIS" in app.strengths
            assert len(app.gaps) == 1


# ============================================================
# 4. STATUS TRANSITIONS + AUDIT TRAIL
# ============================================================


class TestStatusTransitions:
    @pytest.mark.asyncio
    async def test_full_happy_path(self, fresh_db):
        """identified → staged → approved → sent → at_client → contract"""
        from src.db.connection import get_session
        from src.db.models import Application, StatusHistory

        async with get_session() as session:
            app = Application(
                date_recorded=date.today(), project_title="Lifecycle",
                provider="P", status="identified",
            )
            session.add(app)
            await session.flush()
            app_id = app.id

        transitions = [
            ("identified", "staged", "Matched at 97%", "claude"),
            ("staged", "approved", "Reviewed, looks good", "user"),
            ("approved", "sent", "Submitted via freelancermap", "claude"),
            ("sent", "at_client", "Forwarded to end client", "system"),
            ("at_client", "contract", "Signed!", "user"),
        ]

        for old, new, comment, who in transitions:
            async with get_session() as session:
                app = await session.get(Application, app_id)
                app.status = new
                session.add(StatusHistory(
                    application_id=app_id, old_status=old, new_status=new,
                    comment=comment, changed_by=who,
                ))

        async with get_session() as session:
            app = await session.get(Application, app_id)
            assert app.status == "contract"

            history = (await session.execute(
                select(StatusHistory)
                .where(StatusHistory.application_id == app_id)
                .order_by(StatusHistory.id)
            )).scalars().all()

            assert len(history) == 5
            assert history[0].old_status == "identified"
            assert history[-1].new_status == "contract"
            assert history[-1].changed_by == "user"

    @pytest.mark.asyncio
    async def test_rejection_path(self, fresh_db):
        """identified → staged → rejected"""
        from src.db.connection import get_session
        from src.db.models import Application, StatusHistory

        async with get_session() as session:
            app = Application(
                date_recorded=date.today(), project_title="Rejected",
                provider="P", status="identified",
            )
            session.add(app)
            await session.flush()
            app_id = app.id

        async with get_session() as session:
            app = await session.get(Application, app_id)
            app.status = "rejected"
            session.add(StatusHistory(
                application_id=app_id, old_status="identified",
                new_status="rejected", comment="3 month too short",
            ))

        async with get_session() as session:
            app = await session.get(Application, app_id)
            assert app.status == "rejected"

    @pytest.mark.asyncio
    async def test_history_timestamps_ordered(self, fresh_db):
        from src.db.connection import get_session
        from src.db.models import Application, StatusHistory

        async with get_session() as session:
            app = Application(
                date_recorded=date.today(), project_title="Ordered",
                provider="P", status="identified",
            )
            session.add(app)
            await session.flush()
            app_id = app.id

            for s in ["staged", "approved", "sent"]:
                app = await session.get(Application, app_id)
                old = app.status
                app.status = s
                session.add(StatusHistory(
                    application_id=app_id, old_status=old, new_status=s,
                ))
                await session.flush()

        async with get_session() as session:
            history = (await session.execute(
                select(StatusHistory)
                .where(StatusHistory.application_id == app_id)
                .order_by(StatusHistory.id)
            )).scalars().all()

            for i in range(1, len(history)):
                assert history[i].changed_at >= history[i - 1].changed_at


# ============================================================
# 5. MATCH CYCLE TRACKING
# ============================================================


class TestMatchCycles:
    @pytest.mark.asyncio
    async def test_create_and_read_cycle(self, fresh_db):
        from src.db.connection import get_session
        from src.db.models import MatchCycle

        async with get_session() as session:
            session.add(MatchCycle(
                cycle_id="2026-02-08T18:45:00Z",
                leads_found=6, leads_qualified=5, leads_staged=5,
                search_params={"keywords": ["DevOps", "K8s"], "min_score": 70},
                notifications_sent={"gitlab_todo": True, "email": True},
                completed_at=datetime.now(tz=None),
            ))

        async with get_session() as session:
            cycle = (await session.execute(
                select(MatchCycle).where(MatchCycle.cycle_id == "2026-02-08T18:45:00Z")
            )).scalar_one()

        assert cycle.leads_found == 6
        assert cycle.search_params["min_score"] == 70
        assert cycle.notifications_sent["email"] is True

    @pytest.mark.asyncio
    async def test_cycle_id_unique(self, fresh_db):
        from src.db.connection import get_session
        from src.db.models import MatchCycle

        async with get_session() as session:
            session.add(MatchCycle(
                cycle_id="unique", leads_found=0, leads_qualified=0, leads_staged=0,
            ))

        with pytest.raises(Exception):
            async with get_session() as session:
                session.add(MatchCycle(
                    cycle_id="unique", leads_found=0, leads_qualified=0, leads_staged=0,
                ))


# ============================================================
# 6. QUERY PATTERNS (ANALYTICS)
# ============================================================


class TestQueryPatterns:
    @pytest_asyncio.fixture
    async def seeded_db(self, fresh_db, sample_csv):
        from src.db.migrate_csv import migrate_csv
        await migrate_csv(str(sample_csv))

    @pytest.mark.asyncio
    async def test_status_distribution(self, seeded_db):
        from src.db.connection import get_session
        from src.db.models import Application

        async with get_session() as session:
            rows = (await session.execute(
                select(Application.status, func.count().label("c"))
                .group_by(Application.status)
            )).all()

        dist = {r[0]: r[1] for r in rows}
        assert sum(dist.values()) == 5
        assert "sent" in dist
        assert "identified" in dist
        assert "rejected" in dist

    @pytest.mark.asyncio
    async def test_active_leads_filter(self, seeded_db):
        from src.db.connection import get_session
        from src.db.models import Application

        async with get_session() as session:
            active = (await session.execute(
                select(Application).where(
                    Application.status.in_(["identified", "staged", "approved"])
                )
            )).scalars().all()

        assert len(active) == 1
        assert active[0].project_title == "Cloud Architect - Cloud-Transformation"

    @pytest.mark.asyncio
    async def test_monthly_aggregation(self, seeded_db):
        from src.db.connection import get_session

        async with get_session() as session:
            rows = (await session.execute(text("""
                SELECT strftime('%Y-%m', date_recorded) as month, COUNT(*) as c
                FROM applications GROUP BY month ORDER BY month
            """))).all()

        months = {r[0]: r[1] for r in rows}
        assert "2026-02" in months
        assert sum(months.values()) == 5

    @pytest.mark.asyncio
    async def test_sort_newest_first(self, seeded_db):
        from src.db.connection import get_session
        from src.db.models import Application

        async with get_session() as session:
            apps = (await session.execute(
                select(Application).order_by(Application.date_recorded.desc())
            )).scalars().all()

        dates = [a.date_recorded for a in apps]
        assert dates == sorted(dates, reverse=True)

    @pytest.mark.asyncio
    async def test_text_search(self, seeded_db):
        from src.db.connection import get_session
        from src.db.models import Application

        async with get_session() as session:
            results = (await session.execute(
                select(Application).where(
                    Application.project_title.ilike("%K8s%")
                )
            )).scalars().all()

        assert len(results) == 1
        assert "K8s" in results[0].project_title


# ============================================================
# 7. GITLAB ISSUE LINKING
# ============================================================


class TestGitLabLinking:
    @pytest.mark.asyncio
    async def test_store_and_find_by_issue(self, fresh_db):
        from src.db.connection import get_session
        from src.db.models import Application

        async with get_session() as session:
            session.add(Application(
                date_recorded=date.today(), project_title="With Issue",
                provider="P", status="staged",
                gitlab_issue_iid=49,
                gitlab_issue_url="https://gitlab.com/.../issues/49",
            ))
            session.add(Application(
                date_recorded=date.today(), project_title="Without Issue",
                provider="P", status="sent",
            ))

        async with get_session() as session:
            app = (await session.execute(
                select(Application).where(Application.gitlab_issue_iid == 49)
            )).scalar_one()

        assert app.project_title == "With Issue"
        assert "issues/49" in app.gitlab_issue_url


# ============================================================
# 8. DATA INTEGRITY
# ============================================================


class TestDataIntegrity:
    @pytest.mark.asyncio
    async def test_all_enum_values_valid(self, fresh_db, sample_csv):
        from src.db.migrate_csv import migrate_csv
        from src.db.connection import get_session
        from src.db.models import Application, ApplicationStatus

        await migrate_csv(str(sample_csv))

        valid = {s.value for s in ApplicationStatus}
        async with get_session() as session:
            rows = (await session.execute(select(Application.status).distinct())).all()
            db_statuses = {r[0] for r in rows}

        invalid = db_statuses - valid
        assert not invalid, f"Invalid status values: {invalid}"


# ============================================================
# 9. CSV EXPORT ROUNDTRIP
# ============================================================


class TestCSVRoundtrip:
    @pytest.mark.asyncio
    async def test_export_preserves_data(self, fresh_db, sample_csv, tmp_path):
        from src.db.migrate_csv import migrate_csv
        from src.db.connection import get_session
        from src.db.models import Application

        await migrate_csv(str(sample_csv))

        async with get_session() as session:
            apps = (await session.execute(
                select(Application).order_by(Application.date_recorded.desc())
            )).scalars().all()

        export_path = tmp_path / "export.csv"
        fields = [
            "date_recorded", "project_title", "provider", "location",
            "rate_eur_h", "status", "notes",
        ]
        with open(export_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for a in apps:
                writer.writerow({
                    "date_recorded": str(a.date_recorded),
                    "project_title": a.project_title,
                    "provider": a.provider,
                    "location": a.location or "",
                    "rate_eur_h": a.rate_eur_h or "",
                    "status": a.status,
                    "notes": a.notes or "",
                })

        with open(export_path, "r", encoding="utf-8") as f:
            exported = list(csv.DictReader(f))

        assert len(exported) == 5
        assert exported[0]["project_title"] == "Cloud Architect - Cloud-Transformation"
        assert exported[0]["status"] == "identified"  # Normalized!


# ============================================================
# 10. STATUS NORMALIZER UNIT TESTS
# ============================================================


class TestStatusNormalizer:
    def test_simple_sent(self):
        from src.db.migrate_csv import normalize_status
        from src.db.models import ApplicationStatus
        assert normalize_status("versendet")[0] == ApplicationStatus.SENT

    def test_sent_with_date(self):
        from src.db.migrate_csv import normalize_status
        from src.db.models import ApplicationStatus
        s, d, _ = normalize_status("versendet (23.01.2026)")
        assert s == ApplicationStatus.SENT
        assert d == date(2026, 1, 23)

    def test_rejected_variants(self):
        from src.db.migrate_csv import normalize_status
        from src.db.models import ApplicationStatus
        for raw in ["abgelehnt", "Absage", "ABSAGE (beidseitig)", "Position bereits besetzt (11.11.2025)"]:
            assert normalize_status(raw)[0] == ApplicationStatus.REJECTED, f"Failed: {raw}"

    def test_no_response(self):
        from src.db.migrate_csv import normalize_status
        from src.db.models import ApplicationStatus
        assert normalize_status("keine Rueckmeldung (versendet 2025-10-06)")[0] == ApplicationStatus.NO_RESPONSE

    def test_compound_statuses(self):
        from src.db.migrate_csv import normalize_status
        from src.db.models import ApplicationStatus
        assert normalize_status("wird beim Kunden vorgestellt")[0] == ApplicationStatus.AT_CLIENT
        assert normalize_status("Vertrag erhalten (06.11.2025)")[0] == ApplicationStatus.CONTRACT
        assert normalize_status("in Verhandlung (15.12.2025)")[0] == ApplicationStatus.IN_NEGOTIATION

    def test_interview(self):
        from src.db.migrate_csv import normalize_status
        from src.db.models import ApplicationStatus
        s, _, _ = normalize_status("Kunde findet Profil sehr spannend - Interview-Feedback")
        assert s == ApplicationStatus.INTERVIEW

    def test_numeric_is_rate(self):
        from src.db.migrate_csv import normalize_status
        from src.db.models import ApplicationStatus
        s, _, detail = normalize_status("105")
        assert s == ApplicationStatus.SENT
        assert "rate_in_status_field" in detail

    def test_identified(self):
        from src.db.migrate_csv import normalize_status
        from src.db.models import ApplicationStatus
        assert normalize_status("neu identifiziert")[0] == ApplicationStatus.IDENTIFIED
        assert normalize_status("vorbereitet")[0] == ApplicationStatus.IDENTIFIED

    def test_not_applied(self):
        from src.db.migrate_csv import normalize_status
        from src.db.models import ApplicationStatus
        assert normalize_status("nicht beworben")[0] == ApplicationStatus.NOT_APPLIED


# ============================================================
# 11. PRODUCTION CSV (optional, skipped if not available)
# ============================================================


class TestProductionCSV:
    PROD_CSV = "/mnt/user-data/outputs/bewerbungen_komplett_SORTED_Feb_08_2026.csv"

    @pytest.fixture
    def has_prod_csv(self):
        if not Path(self.PROD_CSV).exists():
            pytest.skip("Production CSV not available in this environment")

    @pytest.mark.asyncio
    async def test_migrate_all_193_rows(self, fresh_db, has_prod_csv):
        from src.db.migrate_csv import migrate_csv
        stats = await migrate_csv(self.PROD_CSV)
        assert stats["imported"] == 193
        assert stats["skipped"] == 0
        assert stats["db_count"] == 193

    @pytest.mark.asyncio
    async def test_no_unmapped_statuses(self, fresh_db, has_prod_csv):
        from src.db.migrate_csv import migrate_csv
        stats = await migrate_csv(self.PROD_CSV, dry_run=True)
        unmapped = [k for k in stats["status_mappings"] if "unmapped" in k]
        assert not unmapped, f"Unmapped: {unmapped}"

    @pytest.mark.asyncio
    async def test_all_statuses_valid_enums(self, fresh_db, has_prod_csv):
        from src.db.migrate_csv import migrate_csv
        from src.db.connection import get_session
        from src.db.models import Application, ApplicationStatus

        await migrate_csv(self.PROD_CSV)
        valid = {s.value for s in ApplicationStatus}

        async with get_session() as session:
            rows = (await session.execute(select(Application.status).distinct())).all()
        invalid = {r[0] for r in rows} - valid
        assert not invalid, f"Invalid statuses: {invalid}"

    @pytest.mark.asyncio
    async def test_all_rates_sane(self, fresh_db, has_prod_csv):
        from src.db.migrate_csv import migrate_csv
        from src.db.connection import get_session
        from src.db.models import Application

        await migrate_csv(self.PROD_CSV)

        async with get_session() as session:
            apps = (await session.execute(select(Application))).scalars().all()
            for a in apps:
                assert a.rate_eur_h is not None, f"Null rate: {a.project_title}"
                assert 50 <= a.rate_eur_h <= 300, f"Bad rate {a.rate_eur_h}: {a.project_title}"

    @pytest.mark.asyncio
    async def test_all_dates_sane(self, fresh_db, has_prod_csv):
        from src.db.migrate_csv import migrate_csv
        from src.db.connection import get_session
        from src.db.models import Application

        await migrate_csv(self.PROD_CSV)

        async with get_session() as session:
            apps = (await session.execute(select(Application))).scalars().all()
            for a in apps:
                assert a.date_recorded >= date(2025, 1, 1)
                assert a.date_recorded <= date(2027, 1, 1)
