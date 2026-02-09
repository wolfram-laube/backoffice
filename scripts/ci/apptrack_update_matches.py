#!/usr/bin/env python3
"""Update match scores on AppTrack crawl_results from match pipeline output.

Reads output/matches.json and updates match_score + match_reasons on
crawl_results in GCS-managed SQLite.

Usage:
    # CI (with GCS)
    python scripts/ci/apptrack_update_matches.py

    # Local
    python scripts/ci/apptrack_update_matches.py --db /tmp/applications.db
"""
import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from modules.applications.database import gcs_managed_db, get_engine, get_session
from modules.applications.crawl_service import update_matches_from_file

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Update match scores in AppTrack DB")
    parser.add_argument(
        "--matches",
        type=Path,
        default=Path("output/matches.json"),
        help="Path to match output (default: output/matches.json)",
    )
    parser.add_argument("--profile", default="wolfram", help="Match profile (default: wolfram)")
    parser.add_argument("--db", type=Path, default=None, help="Local SQLite path (skip GCS)")
    parser.add_argument("--no-gcs", action="store_true", help="Don't use GCS")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not args.matches.exists():
        logger.error(f"Matches file not found: {args.matches}")
        sys.exit(1)

    if args.db or args.no_gcs:
        if args.db:
            os.environ["APPTRACK_DB_PATH"] = str(args.db)
        engine = get_engine(args.db)
        with get_session(engine) as session:
            stats = update_matches_from_file(session, args.matches, args.profile)
        engine.dispose()
    else:
        with gcs_managed_db() as engine:
            with get_session(engine) as session:
                stats = update_matches_from_file(session, args.matches, args.profile)

    logger.info(f"✓ Matched: {stats['matched']}, not found: {stats['not_found']}")


if __name__ == "__main__":
    main()
