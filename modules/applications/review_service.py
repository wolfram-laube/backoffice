"""Vorhölle — Review Layer for Match Staging (Sprint 4, ADR-004).

Introduces a human-review step between automated matching and application
creation. CrawlResults with high match scores enter "pending_review" status
and must be explicitly approved or dismissed before becoming Applications.

Status Flow (updated):
    new → matched → pending_review → applied  (creates Application)
                                   → dismissed (with reason)

Usage:
    from modules.applications.review_service import (
        promote_to_review,
        approve_crawl_result,
        dismiss_crawl_result,
        get_review_queue,
    )
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from .crawl_service import stage_to_application
from .models import CrawlResult

logger = logging.getLogger(__name__)

# Valid CrawlResult statuses (extended with review states)
CRAWL_STATUSES = {"new", "matched", "pending_review", "applied", "dismissed"}


# ---------------------------------------------------------------------------
# 1) Promote matched → pending_review
# ---------------------------------------------------------------------------

def promote_to_review(
    session: Session,
    min_score: int = 70,
) -> dict:
    """Move matched CrawlResults (score >= threshold) into pending_review.

    Idempotent: only processes status='matched' records.

    Args:
        session: SQLAlchemy session (caller manages commit)
        min_score: Minimum match_score to enter review (default: 70)

    Returns:
        {"promoted": N, "total_matched": N, "below_threshold": N}
    """
    matched = (
        session.query(CrawlResult)
        .filter(CrawlResult.status == "matched")
        .all()
    )

    promoted = 0
    below = 0
    for cr in matched:
        score = cr.match_score or 0
        if score >= min_score:
            cr.status = "pending_review"
            promoted += 1
            logger.debug(
                f"Promoted to review: {cr.source}/{cr.external_id} "
                f"(score={score})"
            )
        else:
            below += 1

    stats = {
        "promoted": promoted,
        "total_matched": len(matched),
        "below_threshold": below,
    }
    logger.info(
        f"Review promotion: {promoted} promoted, {below} below threshold "
        f"(of {len(matched)} matched, min_score={min_score})"
    )
    return stats


# ---------------------------------------------------------------------------
# 2) Approve: pending_review → applied (creates Application)
# ---------------------------------------------------------------------------

def approve_crawl_result(
    session: Session,
    crawl_result_id: int,
) -> dict:
    """Approve a pending_review CrawlResult — creates an Application.

    Args:
        session: SQLAlchemy session
        crawl_result_id: CrawlResult.id to approve

    Returns:
        {"approved": bool, "application_id": int|None, "error": str|None}
    """
    cr = session.get(CrawlResult, crawl_result_id)
    if cr is None:
        return {"approved": False, "application_id": None,
                "error": f"CrawlResult {crawl_result_id} not found"}

    if cr.status != "pending_review":
        return {"approved": False, "application_id": None,
                "error": f"Cannot approve: status is '{cr.status}' "
                         f"(expected 'pending_review')"}

    app = stage_to_application(session, cr)
    logger.info(
        f"Approved: {cr.source}/{cr.external_id} → Application "
        f"'{app.project_title}'"
    )
    return {"approved": True, "application_id": app.id, "error": None}


# ---------------------------------------------------------------------------
# 3) Dismiss: pending_review → dismissed
# ---------------------------------------------------------------------------

def dismiss_crawl_result(
    session: Session,
    crawl_result_id: int,
    reason: Optional[str] = None,
) -> dict:
    """Dismiss a pending_review CrawlResult.

    Stores dismissal reason in match_reasons dict for audit trail.

    Args:
        session: SQLAlchemy session
        crawl_result_id: CrawlResult.id to dismiss
        reason: Optional dismissal reason

    Returns:
        {"dismissed": bool, "error": str|None}
    """
    cr = session.get(CrawlResult, crawl_result_id)
    if cr is None:
        return {"dismissed": False,
                "error": f"CrawlResult {crawl_result_id} not found"}

    if cr.status != "pending_review":
        return {"dismissed": False,
                "error": f"Cannot dismiss: status is '{cr.status}' "
                         f"(expected 'pending_review')"}

    cr.status = "dismissed"
    # Store reason in match_reasons for audit
    reasons = cr.match_reasons or {}
    reasons["dismissed_reason"] = reason or "Manual dismissal"
    reasons["dismissed_at"] = datetime.now(timezone.utc).isoformat()
    cr.match_reasons = reasons

    logger.info(
        f"Dismissed: {cr.source}/{cr.external_id} "
        f"(reason: {reason or 'none'})"
    )
    return {"dismissed": True, "error": None}


# ---------------------------------------------------------------------------
# 4) Review Queue: list pending_review items
# ---------------------------------------------------------------------------

def get_review_queue(
    session: Session,
    sort_by: str = "score_desc",
) -> list[dict]:
    """Get all CrawlResults in pending_review status.

    Args:
        session: SQLAlchemy session
        sort_by: 'score_desc' (default), 'score_asc', 'date_desc', 'date_asc'

    Returns:
        List of dicts with review queue items
    """
    query = session.query(CrawlResult).filter(
        CrawlResult.status == "pending_review"
    )

    if sort_by == "score_desc":
        query = query.order_by(CrawlResult.match_score.desc())
    elif sort_by == "score_asc":
        query = query.order_by(CrawlResult.match_score.asc())
    elif sort_by == "date_desc":
        query = query.order_by(CrawlResult.crawled_at.desc())
    elif sort_by == "date_asc":
        query = query.order_by(CrawlResult.crawled_at.asc())

    items = []
    for cr in query.all():
        raw = cr.raw_data or {}
        reasons = cr.match_reasons or {}
        items.append({
            "id": cr.id,
            "source": cr.source,
            "external_id": cr.external_id,
            "title": cr.title,
            "match_score": cr.match_score,
            "is_ai": reasons.get("is_ai", False),
            "keywords": reasons.get("keywords", []),
            "company": raw.get("company", raw.get("provider", "—")),
            "location": raw.get("location", "—"),
            "remote_percent": raw.get("remote_percent"),
            "url": raw.get("url", ""),
            "crawled_at": cr.crawled_at.isoformat() if cr.crawled_at else None,
        })

    logger.info(f"Review queue: {len(items)} items pending")
    return items


# ---------------------------------------------------------------------------
# 5) Bulk operations
# ---------------------------------------------------------------------------

def approve_all_above(
    session: Session,
    min_score: int = 90,
) -> dict:
    """Auto-approve all pending_review items above a high threshold.

    Use for fast-tracking obviously great matches.

    Returns:
        {"approved": N, "total": N, "errors": []}
    """
    queue = (
        session.query(CrawlResult)
        .filter(
            CrawlResult.status == "pending_review",
            CrawlResult.match_score >= min_score,
        )
        .all()
    )

    approved = 0
    errors = []
    for cr in queue:
        result = approve_crawl_result(session, cr.id)
        if result["approved"]:
            approved += 1
        else:
            errors.append({"id": cr.id, "error": result["error"]})

    stats = {"approved": approved, "total": len(queue), "errors": errors}
    logger.info(f"Bulk approve: {approved} of {len(queue)} (score >= {min_score})")
    return stats


def get_review_summary(session: Session) -> dict:
    """Get summary statistics for the review queue.

    Returns:
        Dict with counts by status and score distribution
    """
    from sqlalchemy import func

    counts = {}
    for status in CRAWL_STATUSES:
        count = (
            session.query(func.count(CrawlResult.id))
            .filter(CrawlResult.status == status)
            .scalar()
        )
        counts[status] = count

    # Score distribution for pending_review
    pending = (
        session.query(CrawlResult)
        .filter(CrawlResult.status == "pending_review")
        .all()
    )
    scores = [cr.match_score or 0 for cr in pending]

    return {
        "status_counts": counts,
        "pending_count": counts.get("pending_review", 0),
        "score_distribution": {
            "min": min(scores) if scores else 0,
            "max": max(scores) if scores else 0,
            "avg": round(sum(scores) / len(scores), 1) if scores else 0,
        },
    }
