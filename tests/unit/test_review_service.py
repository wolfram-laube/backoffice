"""Tests for Vorhölle Review Service — Sprint 4 (ADR-004).

Covers:
  - Promote matched → pending_review (threshold logic)
  - Approve pending_review → applied (Application creation)
  - Dismiss pending_review → dismissed (with reason)
  - Review queue listing and sorting
  - Bulk operations (approve_all_above)
  - Summary statistics
  - Edge cases: idempotency, invalid states, missing records
  - Re-run safety
"""
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from modules.applications.models import Base, Application, CrawlResult
from modules.applications.review_service import (
    promote_to_review,
    approve_crawl_result,
    dismiss_crawl_result,
    get_review_queue,
    approve_all_above,
    get_review_summary,
    CRAWL_STATUSES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


def _make_crawl(session, source="freelancermap", ext_id="12345",
                title="DevOps Engineer", score=85, status="matched",
                raw_data=None, match_reasons=None):
    """Helper: create a CrawlResult."""
    cr = CrawlResult(
        source=source,
        external_id=ext_id,
        title=title,
        match_score=score,
        status=status,
        raw_data=raw_data or {
            "url": f"https://freelancermap.de/projekt/{ext_id}",
            "company": "TestCorp GmbH",
            "location": "Berlin",
            "remote_percent": 80,
        },
        match_reasons=match_reasons or {
            "keywords": ["kubernetes", "aws"],
            "is_ai": False,
            "profile": "wolfram",
        },
        crawled_at=datetime.now(timezone.utc),
    )
    session.add(cr)
    session.flush()
    return cr


# ---------------------------------------------------------------------------
# TestPromoteToReview
# ---------------------------------------------------------------------------

class TestPromoteToReview:
    """Test promote_to_review: matched → pending_review."""

    def test_promote_above_threshold(self, session):
        cr = _make_crawl(session, ext_id="1", score=85, status="matched")
        stats = promote_to_review(session, min_score=70)
        assert stats["promoted"] == 1
        assert stats["below_threshold"] == 0
        assert cr.status == "pending_review"

    def test_skip_below_threshold(self, session):
        cr = _make_crawl(session, ext_id="1", score=50, status="matched")
        stats = promote_to_review(session, min_score=70)
        assert stats["promoted"] == 0
        assert stats["below_threshold"] == 1
        assert cr.status == "matched"

    def test_skip_non_matched_status(self, session):
        _make_crawl(session, ext_id="1", score=90, status="new")
        _make_crawl(session, ext_id="2", score=90, status="applied")
        _make_crawl(session, ext_id="3", score=90, status="dismissed")
        stats = promote_to_review(session, min_score=70)
        assert stats["promoted"] == 0
        assert stats["total_matched"] == 0

    def test_multiple_records(self, session):
        _make_crawl(session, ext_id="1", score=90, status="matched")
        _make_crawl(session, ext_id="2", score=75, status="matched")
        _make_crawl(session, ext_id="3", score=50, status="matched")
        stats = promote_to_review(session, min_score=70)
        assert stats["promoted"] == 2
        assert stats["below_threshold"] == 1

    def test_idempotent_rerun(self, session):
        cr = _make_crawl(session, ext_id="1", score=85, status="matched")
        promote_to_review(session, min_score=70)
        assert cr.status == "pending_review"
        # Second run: already pending_review, not matched
        stats = promote_to_review(session, min_score=70)
        assert stats["promoted"] == 0
        assert cr.status == "pending_review"

    def test_custom_threshold(self, session):
        _make_crawl(session, ext_id="1", score=85, status="matched")
        stats = promote_to_review(session, min_score=90)
        assert stats["promoted"] == 0
        assert stats["below_threshold"] == 1

    def test_none_score_treated_as_zero(self, session):
        cr = _make_crawl(session, ext_id="1", score=None, status="matched")
        cr.match_score = None
        stats = promote_to_review(session, min_score=70)
        assert stats["promoted"] == 0
        assert stats["below_threshold"] == 1

    def test_exact_threshold(self, session):
        cr = _make_crawl(session, ext_id="1", score=70, status="matched")
        stats = promote_to_review(session, min_score=70)
        assert stats["promoted"] == 1
        assert cr.status == "pending_review"


# ---------------------------------------------------------------------------
# TestApprove
# ---------------------------------------------------------------------------

class TestApprove:
    """Test approve_crawl_result: pending_review → applied."""

    def test_approve_creates_application(self, session):
        cr = _make_crawl(session, ext_id="1", score=85,
                         status="pending_review")
        result = approve_crawl_result(session, cr.id)
        assert result["approved"] is True
        assert result["error"] is None
        assert cr.status == "applied"
        # Check Application was created
        app = session.query(Application).filter_by(
            project_id=cr.external_id
        ).first()
        assert app is not None
        assert app.match_score == 85
        assert app.status == "versendet"

    def test_approve_wrong_status(self, session):
        cr = _make_crawl(session, ext_id="1", score=85, status="matched")
        result = approve_crawl_result(session, cr.id)
        assert result["approved"] is False
        assert "expected 'pending_review'" in result["error"]

    def test_approve_not_found(self, session):
        result = approve_crawl_result(session, 99999)
        assert result["approved"] is False
        assert "not found" in result["error"]

    def test_approve_dismissed_fails(self, session):
        cr = _make_crawl(session, ext_id="1", status="dismissed")
        result = approve_crawl_result(session, cr.id)
        assert result["approved"] is False

    def test_approve_sets_application_fields(self, session):
        cr = _make_crawl(
            session, ext_id="42", score=92, status="pending_review",
            raw_data={
                "url": "https://freelancermap.de/projekt/42",
                "company": "AI Labs GmbH",
                "location": "München",
                "remote_percent": 100,
                "start_date": "März 2026",
                "duration": "12 Monate",
            },
            match_reasons={"keywords": ["llm", "rag"], "is_ai": True,
                           "profile": "wolfram"},
        )
        result = approve_crawl_result(session, cr.id)
        app = session.query(Application).filter_by(project_id="42").first()
        assert app.provider == "AI Labs GmbH"
        assert app.location == "München"
        assert app.rate_eur_h == 105.0
        assert "MATCH 92%" in app.notes
        assert "AI project" in app.notes


# ---------------------------------------------------------------------------
# TestDismiss
# ---------------------------------------------------------------------------

class TestDismiss:
    """Test dismiss_crawl_result: pending_review → dismissed."""

    def test_dismiss_with_reason(self, session):
        cr = _make_crawl(session, ext_id="1", status="pending_review")
        result = dismiss_crawl_result(session, cr.id, reason="Rate too low")
        assert result["dismissed"] is True
        assert cr.status == "dismissed"
        assert cr.match_reasons["dismissed_reason"] == "Rate too low"
        assert "dismissed_at" in cr.match_reasons

    def test_dismiss_without_reason(self, session):
        cr = _make_crawl(session, ext_id="1", status="pending_review")
        result = dismiss_crawl_result(session, cr.id)
        assert result["dismissed"] is True
        assert cr.match_reasons["dismissed_reason"] == "Manual dismissal"

    def test_dismiss_wrong_status(self, session):
        cr = _make_crawl(session, ext_id="1", status="matched")
        result = dismiss_crawl_result(session, cr.id)
        assert result["dismissed"] is False
        assert "expected 'pending_review'" in result["error"]

    def test_dismiss_not_found(self, session):
        result = dismiss_crawl_result(session, 99999)
        assert result["dismissed"] is False
        assert "not found" in result["error"]

    def test_dismiss_preserves_existing_reasons(self, session):
        cr = _make_crawl(
            session, ext_id="1", status="pending_review",
            match_reasons={"keywords": ["k8s"], "is_ai": False,
                           "profile": "wolfram"},
        )
        dismiss_crawl_result(session, cr.id, reason="Not relevant")
        assert cr.match_reasons["keywords"] == ["k8s"]
        assert cr.match_reasons["dismissed_reason"] == "Not relevant"


# ---------------------------------------------------------------------------
# TestReviewQueue
# ---------------------------------------------------------------------------

class TestReviewQueue:
    """Test get_review_queue: listing and sorting."""

    def test_empty_queue(self, session):
        queue = get_review_queue(session)
        assert queue == []

    def test_only_pending_review(self, session):
        _make_crawl(session, ext_id="1", score=90, status="pending_review")
        _make_crawl(session, ext_id="2", score=80, status="matched")
        _make_crawl(session, ext_id="3", score=70, status="applied")
        queue = get_review_queue(session)
        assert len(queue) == 1
        assert queue[0]["external_id"] == "1"

    def test_sort_by_score_desc(self, session):
        _make_crawl(session, ext_id="1", score=70, status="pending_review")
        _make_crawl(session, ext_id="2", score=95, status="pending_review")
        _make_crawl(session, ext_id="3", score=80, status="pending_review")
        queue = get_review_queue(session, sort_by="score_desc")
        scores = [item["match_score"] for item in queue]
        assert scores == [95, 80, 70]

    def test_sort_by_score_asc(self, session):
        _make_crawl(session, ext_id="1", score=70, status="pending_review")
        _make_crawl(session, ext_id="2", score=95, status="pending_review")
        queue = get_review_queue(session, sort_by="score_asc")
        assert queue[0]["match_score"] == 70

    def test_queue_item_fields(self, session):
        _make_crawl(
            session, ext_id="42", score=88, status="pending_review",
            raw_data={"company": "TechCo", "location": "Berlin",
                      "remote_percent": 80,
                      "url": "https://example.com/42"},
            match_reasons={"keywords": ["aws"], "is_ai": True,
                           "profile": "wolfram"},
        )
        queue = get_review_queue(session)
        item = queue[0]
        assert item["id"] is not None
        assert item["source"] == "freelancermap"
        assert item["match_score"] == 88
        assert item["is_ai"] is True
        assert item["company"] == "TechCo"
        assert item["location"] == "Berlin"
        assert item["remote_percent"] == 80
        assert item["crawled_at"] is not None


# ---------------------------------------------------------------------------
# TestBulkOperations
# ---------------------------------------------------------------------------

class TestBulkOperations:
    """Test approve_all_above and get_review_summary."""

    def test_approve_all_above_threshold(self, session):
        _make_crawl(session, ext_id="1", score=95, status="pending_review")
        _make_crawl(session, ext_id="2", score=92, status="pending_review")
        _make_crawl(session, ext_id="3", score=75, status="pending_review")
        result = approve_all_above(session, min_score=90)
        assert result["approved"] == 2
        assert result["total"] == 2
        assert result["errors"] == []
        # 75 should still be pending
        cr3 = session.query(CrawlResult).filter_by(external_id="3").first()
        assert cr3.status == "pending_review"

    def test_review_summary(self, session):
        _make_crawl(session, ext_id="1", score=90, status="new")
        _make_crawl(session, ext_id="2", score=85, status="matched")
        _make_crawl(session, ext_id="3", score=80, status="pending_review")
        _make_crawl(session, ext_id="4", score=70, status="pending_review")
        _make_crawl(session, ext_id="5", score=60, status="applied")
        _make_crawl(session, ext_id="6", score=50, status="dismissed")
        summary = get_review_summary(session)
        assert summary["status_counts"]["pending_review"] == 2
        assert summary["status_counts"]["matched"] == 1
        assert summary["pending_count"] == 2
        assert summary["score_distribution"]["min"] == 70
        assert summary["score_distribution"]["max"] == 80
        assert summary["score_distribution"]["avg"] == 75.0


# ---------------------------------------------------------------------------
# TestCrawlStatuses
# ---------------------------------------------------------------------------

class TestCrawlStatuses:
    """Test status constants."""

    def test_all_statuses_defined(self):
        expected = {"new", "matched", "pending_review", "applied", "dismissed"}
        assert CRAWL_STATUSES == expected

    def test_new_statuses_present(self):
        assert "pending_review" in CRAWL_STATUSES
        assert "dismissed" in CRAWL_STATUSES
