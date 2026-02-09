#!/usr/bin/env python3
"""Export applications database to JSON (for Pages) and CSV (Git fallback).

Outputs:
  public/dashboard.json — Frontend data for GitLab Pages
  output/bewerbungen_export.csv — CSV fallback for Git

Usage:
    # Local (with existing DB)
    python scripts/ci/applications_export_json.py --db /tmp/applications.db

    # CI (with GCS)
    python scripts/ci/applications_export_json.py --gcs
"""
import argparse
import csv
import json
import logging
import os
import sys
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from modules.applications.models import Application, CrawlResult
from modules.applications.database import (
    get_engine,
    get_session,
    download_db,
    get_db_path,
)

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles date/datetime objects."""
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)


def compute_statistics(applications: list[dict]) -> dict:
    """Compute dashboard statistics from applications list."""
    total = len(applications)
    if total == 0:
        return {"total": 0}

    # Status buckets
    status_counts = Counter()
    for app in applications:
        raw = (app.get("status") or "").lower()
        if "versendet" in raw:
            status_counts["versendet"] += 1
        elif "abgelehnt" in raw or "absage" in raw:
            status_counts["abgelehnt"] += 1
        elif "interview" in raw or "telefonat" in raw or "vorgestellt" in raw:
            status_counts["in_kontakt"] += 1
        elif "verhandlung" in raw or "vertrag" in raw:
            status_counts["verhandlung"] += 1
        elif "nicht beworben" in raw:
            status_counts["nicht_beworben"] += 1
        else:
            status_counts["sonstige"] += 1

    # Rate stats
    rates = [a["rate_eur_h"] for a in applications if a.get("rate_eur_h")]
    avg_rate = sum(rates) / len(rates) if rates else 0

    # Match score stats
    scores = [a["match_score"] for a in applications if a.get("match_score")]
    avg_score = sum(scores) / len(scores) if scores else 0

    # Monthly distribution
    monthly = Counter()
    for app in applications:
        d = app.get("date_recorded")
        if d:
            key = d[:7]  # YYYY-MM
            monthly[key] += 1

    # Top providers
    providers = Counter(
        a.get("provider", "Unbekannt") or "Unbekannt"
        for a in applications
    )

    return {
        "total": total,
        "status_distribution": dict(status_counts),
        "rate_avg": round(avg_rate, 1),
        "rate_min": min(rates) if rates else None,
        "rate_max": max(rates) if rates else None,
        "match_score_avg": round(avg_score, 1),
        "with_match_score": len(scores),
        "monthly_distribution": dict(sorted(monthly.items())),
        "top_providers": dict(providers.most_common(15)),
    }


def export_json(
    db_path: Optional[Path] = None,
    output_dir: Path = Path("public"),
) -> Path:
    """Export database to dashboard.json for Pages frontend."""
    engine = get_engine(db_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    with get_session(engine) as session:
        apps = session.query(Application).order_by(
            Application.date_recorded.desc(),
            Application.id.desc(),
        ).all()

        applications = []
        for app in apps:
            applications.append({
                "id": app.id,
                "date_recorded": app.date_recorded.isoformat() if app.date_recorded else None,
                "project_title": app.project_title,
                "provider": app.provider,
                "contact_name": app.contact_name,
                "contact_email": app.contact_email,
                "phone": app.phone,
                "location": app.location,
                "start_date": app.start_date,
                "duration": app.duration,
                "workload": app.workload,
                "rate_eur_h": app.rate_eur_h,
                "status": app.status,
                "match_score": app.match_score,
                "notes": app.notes,
                "source_url": app.source_url,
                "project_id": app.project_id,
            })

        # Crawl results summary
        crawl_count = session.query(CrawlResult).count()
        crawl_new = session.query(CrawlResult).filter(
            CrawlResult.status == "new"
        ).count()

    stats = compute_statistics(applications)

    dashboard = {
        "generated_at": datetime.now(timezone.utc).isoformat() + "Z",
        "statistics": stats,
        "applications": applications,
        "crawl_summary": {
            "total": crawl_count,
            "new": crawl_new,
        },
    }

    output_path = output_dir / "dashboard.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dashboard, f, cls=DateTimeEncoder, ensure_ascii=False, indent=2)

    engine.dispose()
    logger.info(
        f"Exported {len(applications)} applications → {output_path} "
        f"({output_path.stat().st_size / 1024:.1f} KB)"
    )
    return output_path


def export_csv(
    db_path: Optional[Path] = None,
    output_dir: Path = Path("output"),
) -> Path:
    """Export database back to CSV format (Git fallback)."""
    engine = get_engine(db_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "date_recorded", "project_title", "provider", "contact_name",
        "contact_email", "phone", "location", "start", "duration",
        "workload", "rate_eur_h", "status", "notes",
    ]

    with get_session(engine) as session:
        apps = session.query(Application).order_by(
            Application.date_recorded.desc(),
            Application.id.desc(),
        ).all()

        output_path = output_dir / "bewerbungen_export.csv"
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for app in apps:
                writer.writerow({
                    "date_recorded": app.date_recorded.isoformat() if app.date_recorded else "",
                    "project_title": app.project_title or "",
                    "provider": app.provider or "",
                    "contact_name": app.contact_name or "",
                    "contact_email": app.contact_email or "",
                    "phone": app.phone or "",
                    "location": app.location or "",
                    "start": app.start_date or "",
                    "duration": app.duration or "",
                    "workload": app.workload or "",
                    "rate_eur_h": app.rate_eur_h or "",
                    "status": app.status or "",
                    "notes": app.notes or "",
                })

    engine.dispose()
    logger.info(f"Exported {len(apps)} applications → {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Export applications to JSON/CSV")
    parser.add_argument("--db", type=Path, default=None, help="SQLite DB path")
    parser.add_argument("--gcs", action="store_true", help="Download DB from GCS first")
    parser.add_argument(
        "--json-dir", type=Path, default=Path("public"),
        help="Output directory for dashboard.json (default: public/)",
    )
    parser.add_argument(
        "--csv-dir", type=Path, default=Path("output"),
        help="Output directory for CSV export (default: output/)",
    )
    parser.add_argument("--no-csv", action="store_true", help="Skip CSV export")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.db:
        os.environ["APPTRACK_DB_PATH"] = str(args.db)

    if args.gcs:
        download_db()

    db_path = args.db or get_db_path()
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        sys.exit(1)

    # Export JSON
    json_path = export_json(db_path, args.json_dir)
    logger.info(f"✓ JSON export: {json_path}")

    # Export CSV
    if not args.no_csv:
        csv_path = export_csv(db_path, args.csv_dir)
        logger.info(f"✓ CSV export: {csv_path}")


if __name__ == "__main__":
    main()
