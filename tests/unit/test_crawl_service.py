"""Tests for crawl_service — Sprint 2 crawl integration.

Covers:
  - Crawl result ingestion (new, update, dedup, skip)
  - Match score updates
  - Application staging from approved crawl results
  - CRM label mapping
  - Edge cases: missing data, re-runs, idempotency
"""
import json
import pytest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from modules.applications.models import Base, Application, CrawlResult
from modules.applications.crawl_service import (
    extract_external_id,
    normalize_source,
    ingest_crawl_results,
    ingest_from_file,
    update_match_scores,
    stage_to_application,
    stage_all_approved,
    get_crm_label,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    """In-memory SQLite engine."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    """Session with auto-rollback."""
    with Session(engine) as s:
        yield s


@pytest.fixture
def sample_projects():
    """Sample crawl output matching the freelancermap format."""
    return [
        {
            "title": "Senior DevOps Engineer — Kubernetes/AWS",
            "url": "https://www.freelancermap.de/projekt/12345-senior-devops",
            "company": "TechCorp GmbH",
            "location": "München",
            "remote_percent": 80,
            "duration": "6 Monate",
            "start_date": "März 2026",
            "description": "DevOps CI/CD Kubernetes AWS Terraform",
            "source": "freelancermap",
        },
        {
            "title": "Python ML Engineer — RAG Pipeline",
            "url": "https://www.freelancermap.de/projekt/67890-python-ml",
            "company": "AI Startup AG",
            "location": "Berlin",
            "remote_percent": 100,
            "duration": "12 Monate",
            "start_date": "ASAP",
            "description": "Python ML LLM RAG NLP",
            "source": "freelancermap",
        },
        {
            "title": "Cloud Architect — Azure Migration",
            "url": "https://www.freelancermap.de/projekt/11111-cloud-architect",
            "company": "BigBank AG",
            "location": "Frankfurt",
            "remote_percent": 60,
            "duration": "9 Monate",
            "start_date": "April 2026",
            "description": "Azure Cloud Migration Enterprise",
            "source": "freelancermap",
        },
    ]


@pytest.fixture
def sample_matches():
    """Sample matches.json structure."""
    return {
        "total_projects": 20,
        "with_descriptions": 15,
        "profiles": {
            "wolfram": {
                "count": 3,
                "hot": 2,
                "ai_count": 1,
                "top": [
                    {
                        "project": {
                            "title": "Senior DevOps Engineer — Kubernetes/AWS",
                            "url": "https://www.freelancermap.de/projekt/12345-senior-devops",
                            "source": "freelancermap",
                        },
                        "score": 92,
                        "keywords": ["Kubernetes", "AWS", "DevOps", "CI/CD"],
                        "is_ai": False,
                    },
                    {
                        "project": {
                            "title": "Python ML Engineer — RAG Pipeline",
                            "url": "https://www.freelancermap.de/projekt/67890-python-ml",
                            "source": "freelancermap",
                        },
                        "score": 85,
                        "keywords": ["Python", "ML", "LLM", "RAG"],
                        "is_ai": True,
                    },
                    {
                        "project": {
                            "title": "Cloud Architect — Azure Migration",
                            "url": "https://www.freelancermap.de/projekt/11111-cloud-architect",
                            "source": "freelancermap",
                        },
                        "score": 45,
                        "keywords": ["Cloud", "Azure"],
                        "is_ai": False,
                    },
                ],
            },
        },
    }


# ---------------------------------------------------------------------------
# Test: Helpers
# ---------------------------------------------------------------------------

class TestExtractExternalId:
    def test_freelancermap_standard(self):
        url = "https://www.freelancermap.de/projekt/12345-senior-devops"
        assert extract_external_id(url, "freelancermap") == "12345"

    def test_freelancermap_projektboerse(self):
        url = "https://www.freelancermap.de/projektboerse/99999"
        assert extract_external_id(url, "freelancermap") == "99999"

    def test_freelancermap_no_number(self):
        url = "https://www.freelancermap.de/other-page"
        result = extract_external_id(url, "freelancermap")
        assert result == "other-page"

    def test_empty_url(self):
        assert extract_external_id("", "freelancermap") == ""

    def test_unknown_source(self):
        url = "https://example.com/job/42"
        assert extract_external_id(url, "gulp") == url


class TestNormalizeSource:
    def test_freelancermap(self):
        assert normalize_source("FreelancerMap") == "freelancermap"

    def test_gulp(self):
        assert normalize_source("GULP") == "gulp"

    def test_empty(self):
        assert normalize_source("") == "unknown"

    def test_custom(self):
        assert normalize_source("hays.de") == "hays"


# ---------------------------------------------------------------------------
# Test: Ingest crawl results
# ---------------------------------------------------------------------------

class TestIngestCrawlResults:
    def test_ingest_new(self, session, sample_projects):
        stats = ingest_crawl_results(session, sample_projects)
        session.flush()

        assert stats["inserted"] == 3
        assert stats["updated"] == 0
        assert stats["skipped"] == 0

        results = session.query(CrawlResult).all()
        assert len(results) == 3

    def test_dedup_on_reimport(self, session, sample_projects):
        """Re-ingesting same projects should update, not duplicate."""
        ingest_crawl_results(session, sample_projects)
        session.flush()

        stats2 = ingest_crawl_results(session, sample_projects)
        session.flush()

        assert stats2["inserted"] == 0
        assert stats2["updated"] == 3
        assert session.query(CrawlResult).count() == 3

    def test_skip_no_title(self, session):
        projects = [{"url": "https://example.com/1", "title": "", "source": "freelancermap"}]
        stats = ingest_crawl_results(session, projects)
        assert stats["skipped"] == 1

    def test_skip_no_url(self, session):
        projects = [{"title": "Some Project", "source": "freelancermap"}]
        stats = ingest_crawl_results(session, projects)
        assert stats["skipped"] == 1

    def test_status_defaults_to_new(self, session, sample_projects):
        ingest_crawl_results(session, sample_projects)
        session.flush()

        cr = session.query(CrawlResult).first()
        assert cr.status == "new"

    def test_raw_data_preserved(self, session, sample_projects):
        ingest_crawl_results(session, sample_projects)
        session.flush()

        cr = session.query(CrawlResult).filter_by(external_id="12345").first()
        assert cr.raw_data["company"] == "TechCorp GmbH"
        assert cr.raw_data["remote_percent"] == 80


class TestIngestFromFile:
    def test_from_file(self, session, sample_projects, tmp_path):
        projects_file = tmp_path / "projects.json"
        projects_file.write_text(json.dumps(sample_projects))

        stats = ingest_from_file(session, projects_file)
        assert stats["inserted"] == 3


# ---------------------------------------------------------------------------
# Test: Match score updates
# ---------------------------------------------------------------------------

class TestUpdateMatchScores:
    def test_update_scores(self, session, sample_projects, sample_matches):
        """Match scores should be written to crawl_results."""
        ingest_crawl_results(session, sample_projects)
        session.flush()

        stats = update_match_scores(session, sample_matches, "wolfram")
        session.flush()

        assert stats["matched"] == 3
        assert stats["not_found"] == 0

        # Check scores
        cr1 = session.query(CrawlResult).filter_by(external_id="12345").first()
        assert cr1.match_score == 92
        assert cr1.match_reasons["profile"] == "wolfram"

        cr2 = session.query(CrawlResult).filter_by(external_id="67890").first()
        assert cr2.match_score == 85
        assert cr2.match_reasons["is_ai"] is True

    def test_status_promoted_to_matched(self, session, sample_projects, sample_matches):
        """CrawlResults with score >= 70 should be promoted to 'matched'."""
        ingest_crawl_results(session, sample_projects)
        session.flush()

        update_match_scores(session, sample_matches, "wolfram")
        session.flush()

        cr_high = session.query(CrawlResult).filter_by(external_id="12345").first()
        assert cr_high.status == "matched"

        cr_low = session.query(CrawlResult).filter_by(external_id="11111").first()
        assert cr_low.status == "new"  # Score 45, not promoted

    def test_not_found_graceful(self, session, sample_matches):
        """Match update with no crawl results should report not_found."""
        stats = update_match_scores(session, sample_matches, "wolfram")
        assert stats["not_found"] == 3
        assert stats["matched"] == 0

    def test_unknown_profile(self, session, sample_projects, sample_matches):
        """Unknown profile should produce zero matches."""
        ingest_crawl_results(session, sample_projects)
        session.flush()

        stats = update_match_scores(session, sample_matches, "nonexistent")
        assert stats["total"] == 0


# ---------------------------------------------------------------------------
# Test: Stage to Application
# ---------------------------------------------------------------------------

class TestStageToApplication:
    def test_stage_single(self, session, sample_projects, sample_matches):
        """Stage a single high-scoring CrawlResult as an Application."""
        ingest_crawl_results(session, sample_projects)
        session.flush()
        update_match_scores(session, sample_matches, "wolfram")
        session.flush()

        cr = session.query(CrawlResult).filter_by(external_id="12345").first()
        app = stage_to_application(session, cr)
        session.flush()

        assert app.project_title == "Senior DevOps Engineer — Kubernetes/AWS"
        assert app.provider == "TechCorp GmbH"
        assert app.match_score == 92
        assert app.rate_eur_h == 105.0
        assert app.status == "versendet"
        assert app.date_recorded == date.today()
        assert "12345" in (app.notes or "")
        assert cr.status == "applied"

    def test_stage_all_approved(self, session, sample_projects, sample_matches):
        """stage_all_approved should only create apps for score >= min."""
        ingest_crawl_results(session, sample_projects)
        session.flush()
        update_match_scores(session, sample_matches, "wolfram")
        session.flush()

        stats = stage_all_approved(session, min_score=70)
        session.flush()

        assert stats["staged"] == 2  # 92% and 85%, not 45%

        apps = session.query(Application).all()
        assert len(apps) == 2

    def test_stage_idempotent(self, session, sample_projects, sample_matches):
        """Re-staging should not create duplicate Applications."""
        ingest_crawl_results(session, sample_projects)
        session.flush()
        update_match_scores(session, sample_matches, "wolfram")
        session.flush()

        stats1 = stage_all_approved(session, min_score=70)
        session.flush()
        assert stats1["staged"] == 2

        # Re-ingest and re-match to reset statuses for test
        # But existing apps should prevent duplication
        cr = session.query(CrawlResult).filter_by(external_id="12345").first()
        cr.status = "matched"  # Reset for test
        session.flush()

        stats2 = stage_all_approved(session, min_score=70)
        session.flush()
        assert stats2["staged"] == 0  # Already exists

        assert session.query(Application).count() == 2

    def test_stage_preserves_ai_flag(self, session, sample_projects, sample_matches):
        """AI project flag should appear in Application notes."""
        ingest_crawl_results(session, sample_projects)
        session.flush()
        update_match_scores(session, sample_matches, "wolfram")
        session.flush()

        stage_all_approved(session, min_score=70)
        session.flush()

        # The AI project (67890)
        app_ai = (
            session.query(Application)
            .filter_by(project_id="67890")
            .first()
        )
        assert "AI project" in (app_ai.notes or "")


# ---------------------------------------------------------------------------
# Test: CRM label mapping
# ---------------------------------------------------------------------------

class TestGetCrmLabel:
    def test_versendet(self):
        assert get_crm_label("versendet") == "status::versendet"

    def test_abgelehnt(self):
        assert get_crm_label("Absage erhalten") == "status::abgelehnt"

    def test_in_kontakt(self):
        assert get_crm_label("Telefonat geplant") == "status::in-kontakt"

    def test_verhandlung(self):
        assert get_crm_label("Verhandlung läuft") == "status::verhandlung"

    def test_unknown(self):
        assert get_crm_label("foo bar") == "status::sonstige"

    def test_none(self):
        assert get_crm_label(None) is None

    def test_empty(self):
        assert get_crm_label("") is None


# ---------------------------------------------------------------------------
# Test: Full pipeline flow
# ---------------------------------------------------------------------------

class TestFullPipelineFlow:
    """End-to-end: crawl → ingest → match → stage."""

    def test_full_flow(self, session, sample_projects, sample_matches):
        # Step 1: Crawl output → DB
        ingest_stats = ingest_crawl_results(session, sample_projects)
        session.flush()
        assert ingest_stats["inserted"] == 3

        # Step 2: Match scores → DB
        match_stats = update_match_scores(session, sample_matches, "wolfram")
        session.flush()
        assert match_stats["matched"] == 3

        # Step 3: Stage approved → Applications
        stage_stats = stage_all_approved(session, min_score=70)
        session.flush()
        assert stage_stats["staged"] == 2

        # Verify final state
        assert session.query(CrawlResult).filter_by(status="applied").count() == 2
        assert session.query(CrawlResult).filter_by(status="new").count() == 1
        assert session.query(Application).count() == 2

        # Verify application content
        app = (
            session.query(Application)
            .filter_by(project_id="12345")
            .first()
        )
        assert app.match_score == 92
        assert app.provider == "TechCorp GmbH"
        assert app.source_url == "https://www.freelancermap.de/projekt/12345-senior-devops"
