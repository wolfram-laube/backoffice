#!/usr/bin/env python3
"""Stage approved CrawlResults as Applications and sync to CRM.

Two steps:
  1. Create Application records from matched CrawlResults (score >= threshold)
  2. Sync Application status → GitLab CRM Issue labels

Usage:
    # CI (with GCS)
    python scripts/ci/apptrack_stage_approved.py

    # Local (no CRM sync)
    python scripts/ci/apptrack_stage_approved.py --db /tmp/applications.db --no-crm
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from modules.applications.database import gcs_managed_db, get_engine, get_session
from modules.applications.crawl_service import stage_all_approved, sync_crm_labels

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Stage approved matches and sync CRM")
    parser.add_argument("--min-score", type=int, default=70, help="Minimum match score (default: 70)")
    parser.add_argument("--db", type=Path, default=None, help="Local SQLite path (skip GCS)")
    parser.add_argument("--no-gcs", action="store_true", help="Don't use GCS")
    parser.add_argument("--no-crm", action="store_true", help="Skip CRM sync")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually create CRM issues")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    gitlab_token = os.environ.get(
        "GITLAB_PRIVATE_TOKEN",
        os.environ.get("GITLAB_TOKEN", os.environ.get("CI_JOB_TOKEN", "")),
    )
    crm_project_id = os.environ.get("CRM_PROJECT_ID", "78171527")

    results = {"stage": {}, "crm": {}}

    if args.db or args.no_gcs:
        if args.db:
            os.environ["APPTRACK_DB_PATH"] = str(args.db)
        engine = get_engine(args.db)
        with get_session(engine) as session:
            results["stage"] = stage_all_approved(session, args.min_score)

        if not args.no_crm and gitlab_token:
            with get_session(engine) as session:
                results["crm"] = sync_crm_labels(
                    session, gitlab_token, crm_project_id,
                    dry_run=args.dry_run,
                )
        engine.dispose()
    else:
        with gcs_managed_db() as engine:
            with get_session(engine) as session:
                results["stage"] = stage_all_approved(session, args.min_score)

            if not args.no_crm and gitlab_token:
                with get_session(engine) as session:
                    results["crm"] = sync_crm_labels(
                        session, gitlab_token, crm_project_id,
                        dry_run=args.dry_run,
                    )

    # Save results
    os.makedirs("output", exist_ok=True)
    with open("output/apptrack_stage_results.json", "w") as f:
        json.dump(results, f, indent=2)

    stage = results["stage"]
    logger.info(f"✓ Staged: {stage.get('staged', 0)} applications")

    if results.get("crm"):
        crm = results["crm"]
        logger.info(
            f"✓ CRM: {crm.get('synced', 0)} updated, "
            f"{crm.get('created', 0)} created"
        )


if __name__ == "__main__":
    main()
