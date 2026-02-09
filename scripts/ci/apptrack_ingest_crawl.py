#!/usr/bin/env python3
"""Ingest crawl pipeline output into AppTrack crawl_results table.

Reads output/projects.json from the crawl stage and writes to
crawl_results table in GCS-managed SQLite.

Usage:
    # CI (with GCS)
    python scripts/ci/apptrack_ingest_crawl.py

    # Local (with existing DB)
    python scripts/ci/apptrack_ingest_crawl.py --db /tmp/applications.db --projects output/projects.json
"""
import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from modules.applications.database import gcs_managed_db, get_engine, get_session, init_db
from modules.applications.crawl_service import ingest_from_file

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Ingest crawl results into AppTrack DB")
    parser.add_argument(
        "--projects",
        type=Path,
        default=Path("output/projects.json"),
        help="Path to crawl output (default: output/projects.json)",
    )
    parser.add_argument("--db", type=Path, default=None, help="Local SQLite path (skip GCS)")
    parser.add_argument("--no-gcs", action="store_true", help="Don't use GCS")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not args.projects.exists():
        logger.error(f"Projects file not found: {args.projects}")
        sys.exit(1)

    if args.db or args.no_gcs:
        # Local mode
        if args.db:
            os.environ["APPTRACK_DB_PATH"] = str(args.db)
        engine = get_engine(args.db)
        init_db(engine)
        with get_session(engine) as session:
            stats = ingest_from_file(session, args.projects)
        engine.dispose()
    else:
        # GCS mode
        with gcs_managed_db() as engine:
            init_db(engine)
            with get_session(engine) as session:
                stats = ingest_from_file(session, args.projects)

    if stats["inserted"] == 0 and stats["updated"] == 0:
        logger.warning("No crawl results ingested!")
        sys.exit(2)  # Warning, not failure

    logger.info(f"✓ Ingested: {stats['inserted']} new, {stats['updated']} updated")


if __name__ == "__main__":
    main()
