"""Crawl Integration Service — Sprint 2 (ADR-004).

Bridges the existing crawl/match/stage pipeline with the AppTrack SQLite DB.

Flow:
    crawl output → ingest_crawl_results() → crawl_results table
    match output → update_match_scores()   → match_score on crawl_results
    approved     → stage_to_application()  → applications table
    app status   → sync_crm_labels()       → GitLab Issue labels

All operations are idempotent: safe to re-run.
"""
import json
import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from .models import Application, CrawlResult, ApplicationHistory

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def extract_external_id(url: str, source: str = "freelancermap") -> str:
    """Extract stable external ID from project URL.

    freelancermap: https://www.freelancermap.de/projekt/12345-title → "12345"
    gulp:          project page ID
    """
    if not url:
        return ""

    if "freelancermap" in source.lower():
        # /projekt/12345-some-title or /projektboerse/12345
        m = re.search(r"/projekt(?:boerse)?/(\d+)", url)
        if m:
            return m.group(1)
        # fallback: use full URL path as ID
        return urlparse(url).path.strip("/")

    # Default: use full URL as ID
    return url


def normalize_source(raw: str) -> str:
    """Normalize source platform name."""
    raw = raw.lower().strip()
    if "freelancermap" in raw:
        return "freelancermap"
    if "gulp" in raw:
        return "gulp"
    if "freelance.de" in raw:
        return "freelance.de"
    if "hays" in raw:
        return "hays"
    return raw or "unknown"


# ---------------------------------------------------------------------------
# 1) Ingest crawl results → crawl_results table
# ---------------------------------------------------------------------------

def ingest_crawl_results(
    session: Session,
    projects: list[dict],
) -> dict:
    """Ingest crawled projects into crawl_results table.

    Deduplicates by (source, external_id). Updates raw_data on re-crawl.

    Args:
        session: SQLAlchemy session (caller manages commit)
        projects: List of project dicts from crawl pipeline output

    Returns:
        {"inserted": N, "updated": N, "skipped": N, "total": N}
    """
    stats = {"inserted": 0, "updated": 0, "skipped": 0, "total": len(projects)}

    for project in projects:
        url = project.get("url", "")
        source = normalize_source(project.get("source", "freelancermap"))
        external_id = extract_external_id(url, source)

        if not external_id:
            logger.warning(f"No external_id for: {project.get('title', '?')}")
            stats["skipped"] += 1
            continue

        title = project.get("title", "").strip()
        if not title:
            stats["skipped"] += 1
            continue

        # Check for existing
        existing = (
            session.query(CrawlResult)
            .filter_by(source=source, external_id=external_id)
            .first()
        )

        if existing:
            # Update raw_data on re-crawl (keep match_score, status)
            existing.raw_data = project
            existing.title = title
            stats["updated"] += 1
            logger.debug(f"Updated crawl result: {source}/{external_id}")
        else:
            cr = CrawlResult(
                source=source,
                external_id=external_id,
                title=title,
                raw_data=project,
                status="new",
                crawled_at=datetime.now(timezone.utc),
            )
            session.add(cr)
            stats["inserted"] += 1
            logger.debug(f"Inserted crawl result: {source}/{external_id}")

    logger.info(
        f"Ingest: {stats['inserted']} new, {stats['updated']} updated, "
        f"{stats['skipped']} skipped (of {stats['total']})"
    )
    return stats


def ingest_from_file(
    session: Session,
    projects_json: Path,
) -> dict:
    """Convenience: load projects.json and ingest."""
    with open(projects_json, "r", encoding="utf-8") as f:
        projects = json.load(f)
    return ingest_crawl_results(session, projects)


# ---------------------------------------------------------------------------
# 2) Update match scores from match pipeline output
# ---------------------------------------------------------------------------

def update_match_scores(
    session: Session,
    matches_data: dict,
    profile: str = "wolfram",
) -> dict:
    """Update match_score and match_reasons on crawl_results from matches.json.

    Args:
        session: SQLAlchemy session
        matches_data: Parsed matches.json content
        profile: Which profile's scores to use (default: wolfram)

    Returns:
        {"matched": N, "not_found": N, "total": N}
    """
    profile_data = matches_data.get("profiles", {}).get(profile, {})
    top_matches = profile_data.get("top", [])

    stats = {"matched": 0, "not_found": 0, "total": len(top_matches)}

    for match in top_matches:
        project = match.get("project", {})
        url = project.get("url", "")
        source = normalize_source(project.get("source", "freelancermap"))
        external_id = extract_external_id(url, source)

        if not external_id:
            stats["not_found"] += 1
            continue

        cr = (
            session.query(CrawlResult)
            .filter_by(source=source, external_id=external_id)
            .first()
        )

        if cr:
            score = match.get("score", 0)
            cr.match_score = score
            cr.match_reasons = {
                "keywords": match.get("keywords", []),
                "is_ai": match.get("is_ai", False),
                "profile": profile,
            }
            # Promote status if score qualifies
            if score >= 70 and cr.status == "new":
                cr.status = "matched"

            stats["matched"] += 1
            logger.debug(f"Matched {source}/{external_id}: {score}%")
        else:
            stats["not_found"] += 1
            logger.debug(f"No crawl_result for URL: {url}")

    logger.info(
        f"Match update: {stats['matched']} matched, "
        f"{stats['not_found']} not found (of {stats['total']})"
    )
    return stats


def update_matches_from_file(
    session: Session,
    matches_json: Path,
    profile: str = "wolfram",
) -> dict:
    """Convenience: load matches.json and update scores."""
    with open(matches_json, "r", encoding="utf-8") as f:
        data = json.load(f)
    return update_match_scores(session, data, profile)


# ---------------------------------------------------------------------------
# 3) Stage: create Application from approved CrawlResult
# ---------------------------------------------------------------------------

def stage_to_application(
    session: Session,
    crawl_result: CrawlResult,
) -> Application:
    """Create an Application record from an approved CrawlResult.

    Sets CrawlResult.status = 'applied'.

    Returns:
        New Application record
    """
    raw = crawl_result.raw_data or {}

    app = Application(
        date_recorded=date.today(),
        project_title=crawl_result.title,
        provider=raw.get("company", raw.get("provider", "—")),
        contact_name=raw.get("contact_name"),
        contact_email=raw.get("contact_email"),
        phone=None,
        location=raw.get("location", "Remote"),
        start_date=raw.get("start_date", "ASAP"),
        duration=raw.get("duration"),
        workload=f"{raw.get('remote_percent', 0)}% Remote" if raw.get("remote_percent") else None,
        rate_eur_h=105.0,  # Standard rate
        status="versendet",
        match_score=crawl_result.match_score,
        notes=(
            f"Source: {crawl_result.source}/{crawl_result.external_id} | "
            f"MATCH {crawl_result.match_score}%"
            + (f" | AI project" if (crawl_result.match_reasons or {}).get("is_ai") else "")
        ),
        source_url=raw.get("url"),
        project_id=crawl_result.external_id,
    )
    session.add(app)

    # Update crawl result status
    crawl_result.status = "applied"

    logger.info(
        f"Created Application from crawl {crawl_result.source}/{crawl_result.external_id}"
    )
    return app


def stage_all_approved(
    session: Session,
    min_score: int = 70,
) -> dict:
    """Create Applications from all matched CrawlResults with score >= min_score.

    Only processes CrawlResults with status='matched'.

    Returns:
        {"staged": N, "total_matched": N}
    """
    matched = (
        session.query(CrawlResult)
        .filter(
            CrawlResult.status == "matched",
            CrawlResult.match_score >= min_score,
        )
        .order_by(CrawlResult.match_score.desc())
        .all()
    )

    staged = 0
    for cr in matched:
        # Check if application already exists for this source/external_id
        existing = (
            session.query(Application)
            .filter_by(project_id=cr.external_id)
            .first()
        )
        if existing:
            logger.debug(
                f"Application already exists for {cr.source}/{cr.external_id}"
            )
            cr.status = "applied"  # Mark as applied anyway
            continue

        stage_to_application(session, cr)
        staged += 1

    stats = {"staged": staged, "total_matched": len(matched)}
    logger.info(f"Staged: {staged} new applications (of {len(matched)} matched)")
    return stats


# ---------------------------------------------------------------------------
# 4) CRM Sync: Application status → GitLab Issue labels
# ---------------------------------------------------------------------------

STATUS_TO_LABEL = {
    "versendet": "status::versendet",
    "in_kontakt": "status::in-kontakt",
    "interview": "status::in-kontakt",
    "telefonat": "status::in-kontakt",
    "vorgestellt": "status::in-kontakt",
    "verhandlung": "status::verhandlung",
    "vertrag": "status::verhandlung",
    "abgelehnt": "status::abgelehnt",
    "absage": "status::abgelehnt",
    "nicht_beworben": "status::nicht-beworben",
    "nicht beworben": "status::nicht-beworben",
}


def get_crm_label(status: str) -> Optional[str]:
    """Map application status to CRM issue label."""
    if not status:
        return None
    normalized = status.lower().strip()
    for key, label in STATUS_TO_LABEL.items():
        if key in normalized:
            return label
    return "status::sonstige"


def sync_crm_labels(
    session: Session,
    gitlab_token: str,
    crm_project_id: str = "78171527",
    gitlab_api: str = "https://gitlab.com/api/v4",
    dry_run: bool = False,
) -> dict:
    """Sync Application status changes to GitLab CRM Issue labels.

    Looks for Applications with project_id (crawl-sourced) and syncs
    their status to corresponding CRM issues.

    Returns:
        {"synced": N, "created": N, "skipped": N, "errors": N}
    """
    import requests

    stats = {"synced": 0, "created": 0, "skipped": 0, "errors": 0}

    # Get applications that came from crawl (have project_id)
    apps = (
        session.query(Application)
        .filter(Application.project_id.isnot(None))
        .all()
    )

    headers = {"PRIVATE-TOKEN": gitlab_token}

    for app in apps:
        label = get_crm_label(app.status)
        if not label:
            stats["skipped"] += 1
            continue

        # Search for existing CRM issue
        search_url = f"{gitlab_api}/projects/{crm_project_id}/issues"
        try:
            resp = requests.get(
                search_url,
                headers=headers,
                params={"search": app.project_title[:80], "per_page": 5},
                timeout=10,
            )
            resp.raise_for_status()
            issues = resp.json()
        except Exception as e:
            logger.error(f"CRM search failed for '{app.project_title}': {e}")
            stats["errors"] += 1
            continue

        if issues:
            # Update existing issue labels
            issue = issues[0]
            existing_labels = set(issue.get("labels", []))
            # Remove old status labels
            new_labels = {
                l for l in existing_labels if not l.startswith("status::")
            }
            new_labels.add(label)

            if new_labels != existing_labels and not dry_run:
                try:
                    requests.put(
                        f"{search_url}/{issue['iid']}",
                        headers=headers,
                        json={"labels": ",".join(new_labels)},
                        timeout=10,
                    )
                    stats["synced"] += 1
                except Exception as e:
                    logger.error(f"CRM label update failed: {e}")
                    stats["errors"] += 1
            else:
                stats["skipped"] += 1
        else:
            # Create new CRM issue
            if not dry_run:
                try:
                    resp = requests.post(
                        search_url,
                        headers=headers,
                        json={
                            "title": f"[AppTrack] {app.project_title[:80]}",
                            "labels": f"apptrack,{label}",
                            "description": (
                                f"**Provider:** {app.provider or '—'}\n"
                                f"**Location:** {app.location or '—'}\n"
                                f"**Rate:** {app.rate_eur_h or '—'} EUR/h\n"
                                f"**Match:** {app.match_score or '—'}%\n"
                                f"**Source:** {app.source_url or '—'}\n"
                                f"**Date:** {app.date_recorded}\n"
                            ),
                            "assignee_id": 1349601,
                        },
                        timeout=10,
                    )
                    resp.raise_for_status()
                    stats["created"] += 1
                except Exception as e:
                    logger.error(f"CRM issue creation failed: {e}")
                    stats["errors"] += 1

    logger.info(
        f"CRM sync: {stats['synced']} updated, {stats['created']} created, "
        f"{stats['skipped']} skipped, {stats['errors']} errors"
    )
    return stats
