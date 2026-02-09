"""Tests for Application Tracking System (ADR-004) — Sprint 1.

Covers:
  - SQLAlchemy models (CRUD, relationships, constraints)
  - CSV import (parsing, edge cases, column shift detection)
  - JSON/CSV export (structure, statistics)
  - Auto-history tracking
"""
import csv
import json
import os
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Ensure test DB path
os.environ["APPTRACK_DB_PATH"] = "/tmp/test_applications.db"

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from modules.applications.models import (
    Application,
    ApplicationHistory,
    Base,
    CrawlResult,
)
from modules.applications.database import get_engine, get_session, init_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine(tmp_path):
    """Create a fresh in-memory SQLite engine for each test."""
    db_path = tmp_path / "test.db"
    eng = get_engine(db_path, echo=False)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    """Provide a session that rolls back after each test."""
    with Session(engine) as sess:
        yield sess


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class TestApplicationModel:
    def test_create_application(self, session):
        app = Application(
            date_recorded=date(2026, 1, 15),
            project_title="DevOps Engineer - Cloud Platform",
            provider="GULP",
            status="versendet",
            rate_eur_h=105.0,
            match_score=85,
        )
        session.add(app)
        session.commit()

        assert app.id is not None
        assert app.id > 0
        assert app.project_title == "DevOps Engineer - Cloud Platform"
        assert app.rate_eur_h == 105.0
        assert app.match_score == 85

    def test_application_nullable_fields(self, session):
        """All fields except project_title should be nullable."""
        app = Application(project_title="Minimal Application")
        session.add(app)
        session.commit()

        assert app.id is not None
        assert app.provider is None
        assert app.rate_eur_h is None
        assert app.match_score is None

    def test_application_repr(self, session):
        app = Application(
            date_recorded=date(2026, 1, 15),
            project_title="A" * 100,
            status="versendet",
        )
        session.add(app)
        session.commit()
        repr_str = repr(app)
        assert "Application" in repr_str
        assert "versendet" in repr_str

    def test_multiple_applications(self, session):
        for i in range(10):
            session.add(Application(
                project_title=f"Project {i}",
                date_recorded=date(2026, 1, i + 1),
                status="versendet",
            ))
        session.commit()

        count = session.query(Application).count()
        assert count == 10


class TestCrawlResultModel:
    def test_create_crawl_result(self, session):
        cr = CrawlResult(
            source="gulp",
            external_id="12345",
            title="DevOps Engineer",
            raw_data={"url": "https://gulp.de/12345", "description": "..."},
            match_score=80,
            match_reasons={"strengths": ["K8s", "Python"], "gaps": ["Java"]},
            status="new",
            crawled_at=datetime(2026, 2, 9, 8, 0, 0),
        )
        session.add(cr)
        session.commit()

        assert cr.id is not None
        assert cr.raw_data["url"] == "https://gulp.de/12345"
        assert cr.match_reasons["strengths"] == ["K8s", "Python"]

    def test_unique_constraint_source_external_id(self, session):
        """Duplicate (source, external_id) should raise."""
        cr1 = CrawlResult(
            source="gulp", external_id="99", title="A",
            crawled_at=datetime.now(timezone.utc),
        )
        cr2 = CrawlResult(
            source="gulp", external_id="99", title="B",
            crawled_at=datetime.now(timezone.utc),
        )
        session.add(cr1)
        session.commit()

        session.add(cr2)
        with pytest.raises(Exception):  # IntegrityError
            session.commit()


class TestApplicationHistory:
    def test_history_relationship(self, session):
        app = Application(project_title="Test App", status="versendet")
        session.add(app)
        session.commit()

        hist = ApplicationHistory(
            application_id=app.id,
            field_changed="status",
            old_value="versendet",
            new_value="abgelehnt",
            changed_at=datetime.now(timezone.utc),
        )
        session.add(hist)
        session.commit()

        # Refresh to load relationship
        session.refresh(app)
        assert len(app.history) == 1
        assert app.history[0].field_changed == "status"

    def test_cascade_delete(self, session):
        app = Application(project_title="To Delete")
        session.add(app)
        session.commit()

        hist = ApplicationHistory(
            application_id=app.id,
            field_changed="status",
            old_value=None,
            new_value="versendet",
            changed_at=datetime.now(timezone.utc),
        )
        session.add(hist)
        session.commit()

        session.delete(app)
        session.commit()

        assert session.query(ApplicationHistory).count() == 0


class TestAutoHistory:
    def test_status_change_creates_history(self, session):
        app = Application(project_title="Auto Track", status="versendet")
        session.add(app)
        session.commit()

        # Refresh to load committed state (needed for history tracking)
        session.refresh(app)
        app.status = "abgelehnt"
        session.commit()

        history = session.query(ApplicationHistory).filter_by(
            application_id=app.id
        ).all()
        assert len(history) == 1
        assert history[0].field_changed == "status"
        assert history[0].old_value == "versendet"
        assert history[0].new_value == "abgelehnt"

    def test_untracked_field_no_history(self, session):
        app = Application(project_title="No Track", status="versendet")
        session.add(app)
        session.commit()

        session.refresh(app)
        app.project_title = "Changed Title"
        session.commit()

        history = session.query(ApplicationHistory).filter_by(
            application_id=app.id
        ).all()
        # project_title is NOT in TRACKED_FIELDS
        assert len(history) == 0


# ---------------------------------------------------------------------------
# CSV Import Tests
# ---------------------------------------------------------------------------

from scripts.ci.applications_import_csv import (
    parse_rate,
    parse_match_score,
    parse_date,
    detect_column_shift,
    csv_row_to_application,
    import_csv,
)


class TestParseRate:
    def test_numeric(self):
        assert parse_rate("105") == 105.0
        assert parse_rate("98") == 98.0
        assert parse_rate("105.5") == 105.5

    def test_range(self):
        assert parse_rate("100-110") == 100.0
        assert parse_rate("95-105") == 95.0
        assert parse_rate("85-95") == 85.0

    def test_not_a_rate(self):
        assert parse_rate("100% Vollzeit") is None
        assert parse_rate("nicht angegeben") is None
        assert parse_rate("?") is None
        assert parse_rate("") is None
        assert parse_rate("10 Tage/Monat (20%)") is None

    def test_edge_cases(self):
        assert parse_rate("0") == 0.0
        assert parse_rate("  105  ") == 105.0


class TestParseMatchScore:
    def test_standard(self):
        assert parse_match_score("MATCH 85%!") == 85
        assert parse_match_score("Match 90%+ ENDKUNDE") == 90
        assert parse_match_score("match 100%") == 100

    def test_in_context(self):
        assert parse_match_score(
            "GULP Alert 31.01, 50Hertz-Match 90%+, KRITIS"
        ) == 90

    def test_no_match(self):
        assert parse_match_score("Just regular notes") is None
        assert parse_match_score("") is None
        assert parse_match_score(None) is None


class TestParseDate:
    def test_valid(self):
        assert parse_date("2026-01-15") == date(2026, 1, 15)
        assert parse_date("2025-11-07") == date(2025, 11, 7)

    def test_invalid(self):
        assert parse_date("") is None
        assert parse_date("invalid") is None
        assert parse_date(None) is None


class TestDetectColumnShift:
    def test_normal_row(self):
        row = {"rate_eur_h": "105", "status": "versendet", "workload": "FT", "notes": ""}
        rate, status, workload = detect_column_shift(row)
        assert rate == 105.0
        assert status == "versendet"
        assert workload == "FT"

    def test_shifted_row(self):
        row = {
            "rate_eur_h": "100% Vollzeit",
            "status": "105",
            "workload": "FT",
            "notes": "versendet (15.12.2025)",
        }
        rate, status, workload = detect_column_shift(row)
        assert rate == 105.0
        assert status == "versendet (15.12.2025)"
        assert workload == "100% Vollzeit"

    def test_shifted_row_empty_rate(self):
        """When rate is empty and status is numeric — also a column shift."""
        row = {
            "rate_eur_h": "",
            "status": "105",
            "workload": "FT",
            "notes": "versendet",
        }
        rate, status, workload = detect_column_shift(row)
        assert rate == 105.0
        assert status == "versendet"


class TestCSVImport:
    def test_import_small_csv(self, tmp_path):
        csv_path = tmp_path / "test.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "date_recorded", "project_title", "provider", "contact_name",
                "contact_email", "phone", "location", "start", "duration",
                "workload", "rate_eur_h", "status", "notes",
            ])
            writer.writerow([
                "2026-01-15", "DevOps Engineer K8s", "GULP", "Max Mustermann",
                "max@gulp.de", "+49 123", "Remote", "ASAP", "6 Monate",
                "FT", "105", "versendet", "MATCH 85%! CKA match",
            ])
            writer.writerow([
                "2026-01-10", "Python Backend Dev", "freelancermap", "", "",
                "", "Berlin", "01.03.2026", "12 Monate",
                "FT", "95-105", "versendet", "",
            ])

        db_path = tmp_path / "test.db"
        os.environ["APPTRACK_DB_PATH"] = str(db_path)
        count = import_csv(csv_path, db_path)

        assert count == 2

        engine = get_engine(db_path)
        with Session(engine) as sess:
            apps = sess.query(Application).order_by(Application.id).all()
            assert len(apps) == 2

            assert apps[0].project_title == "DevOps Engineer K8s"
            assert apps[0].rate_eur_h == 105.0
            assert apps[0].match_score == 85
            assert apps[0].status == "versendet"

            assert apps[1].rate_eur_h == 95.0  # range: take lower
            assert apps[1].match_score is None

        engine.dispose()

    def test_import_real_csv(self, tmp_path):
        """Integration test with actual CSV if available."""
        csv_path = Path("/mnt/project/bewerbungen_komplett_SORTED_Jan_31_2026.csv")
        if not csv_path.exists():
            pytest.skip("Real CSV not available")

        db_path = tmp_path / "real.db"
        os.environ["APPTRACK_DB_PATH"] = str(db_path)
        count = import_csv(csv_path, db_path)

        assert count >= 180  # We know there are 187 rows

        engine = get_engine(db_path)
        with Session(engine) as sess:
            total = sess.query(Application).count()
            with_score = sess.query(Application).filter(
                Application.match_score.isnot(None)
            ).count()

            assert total >= 180
            assert with_score >= 50  # We know ~55 have MATCH scores

        engine.dispose()


# ---------------------------------------------------------------------------
# Export Tests
# ---------------------------------------------------------------------------

from scripts.ci.applications_export_json import (
    export_json,
    export_csv,
    compute_statistics,
)


class TestExportJSON:
    def test_export_creates_valid_json(self, engine, tmp_path):
        with Session(engine) as sess:
            for i in range(5):
                sess.add(Application(
                    date_recorded=date(2026, 1, i + 1),
                    project_title=f"Project {i}",
                    provider="TestProvider",
                    status="versendet",
                    rate_eur_h=100.0 + i,
                    match_score=70 + i * 5,
                ))
            sess.commit()

        db_path = Path(str(engine.url).replace("sqlite:///", ""))
        json_path = export_json(db_path, tmp_path / "public")

        assert json_path.exists()
        with open(json_path) as f:
            data = json.load(f)

        assert "generated_at" in data
        assert "statistics" in data
        assert "applications" in data
        assert len(data["applications"]) == 5
        assert data["statistics"]["total"] == 5
        assert data["statistics"]["rate_avg"] > 0

    def test_export_csv_roundtrip(self, engine, tmp_path):
        with Session(engine) as sess:
            sess.add(Application(
                date_recorded=date(2026, 1, 15),
                project_title="Roundtrip Test",
                provider="TestCo",
                status="versendet",
                rate_eur_h=105.0,
                notes="MATCH 90%! Test roundtrip",
            ))
            sess.commit()

        db_path = Path(str(engine.url).replace("sqlite:///", ""))
        csv_path = export_csv(db_path, tmp_path / "output")

        assert csv_path.exists()
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["project_title"] == "Roundtrip Test"
        assert rows[0]["rate_eur_h"] == "105.0"


class TestComputeStatistics:
    def test_empty(self):
        stats = compute_statistics([])
        assert stats["total"] == 0

    def test_status_buckets(self):
        apps = [
            {"status": "versendet", "rate_eur_h": 100, "match_score": 80, "date_recorded": "2026-01"},
            {"status": "versendet (12.11.2025)", "rate_eur_h": 105, "match_score": None, "date_recorded": "2025-11"},
            {"status": "abgelehnt", "rate_eur_h": None, "match_score": None, "date_recorded": "2025-12"},
            {"status": "Telefonat mit HR - Interview", "rate_eur_h": 98, "match_score": 90, "date_recorded": "2026-01"},
        ]
        stats = compute_statistics(apps)
        assert stats["total"] == 4
        assert stats["status_distribution"]["versendet"] == 2
        assert stats["status_distribution"]["abgelehnt"] == 1
        assert stats["status_distribution"]["in_kontakt"] == 1
        assert stats["rate_avg"] == pytest.approx(101.0, abs=0.1)


# ---------------------------------------------------------------------------
# Database Tests
# ---------------------------------------------------------------------------

class TestDatabase:
    def test_init_db_creates_tables(self, tmp_path):
        db_path = tmp_path / "init_test.db"
        engine = get_engine(db_path)
        init_db(engine)

        with Session(engine) as sess:
            # Tables should exist — verify by querying
            assert sess.query(Application).count() == 0
            assert sess.query(CrawlResult).count() == 0
            assert sess.query(ApplicationHistory).count() == 0

        engine.dispose()

    def test_session_context_manager(self, engine):
        with get_session(engine) as sess:
            sess.add(Application(project_title="Session Test"))

        with get_session(engine) as sess:
            assert sess.query(Application).count() == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
