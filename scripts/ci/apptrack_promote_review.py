#!/usr/bin/env python3
"""Promote matched CrawlResults to pending_review and optionally notify.

CI job: apptrack:promote-review
Runs after apptrack:update-matches in the pipeline.

Usage:
    # CI (with GCS)
    python scripts/ci/apptrack_promote_review.py --min-score 70 -v

    # Local
    python scripts/ci/apptrack_promote_review.py --db /tmp/applications.db --no-gcs -v
"""
import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from modules.applications.database import gcs_managed_db, get_engine, get_session
from modules.applications.review_service import (
    promote_to_review,
    get_review_queue,
    get_review_summary,
)

logger = logging.getLogger(__name__)


def _send_notification(queue: list[dict], summary: dict) -> bool:
    """Send notification about new items in review queue.

    Currently logs to stdout; extend with Gmail/Slack integration.
    """
    if not queue:
        logger.info("No items in review queue — skipping notification.")
        return False

    logger.info("=" * 60)
    logger.info("📋 VORHÖLLE REVIEW QUEUE — New items pending review")
    logger.info("=" * 60)
    logger.info(f"  Pending: {summary['pending_count']} items")
    dist = summary["score_distribution"]
    logger.info(
        f"  Scores: min={dist['min']}, max={dist['max']}, avg={dist['avg']}"
    )
    logger.info("-" * 60)
    for item in queue[:10]:
        ai_tag = " 🤖 AI" if item.get("is_ai") else ""
        logger.info(
            f"  [{item['match_score']:3d}%] {item['title'][:60]}{ai_tag}"
        )
        logger.info(
            f"         {item['company']} | {item['location']} | "
            f"{item['source']}/{item['external_id']}"
        )
    if len(queue) > 10:
        logger.info(f"  ... and {len(queue) - 10} more")
    logger.info("=" * 60)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Promote matched crawl results to review queue"
    )
    parser.add_argument(
        "--min-score", type=int, default=70,
        help="Minimum match score for review (default: 70)"
    )
    parser.add_argument("--db", type=Path, default=None, help="Local SQLite path")
    parser.add_argument("--no-gcs", action="store_true", help="Don't use GCS")
    parser.add_argument("--notify", action="store_true", help="Send notification")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    results = {}

    if args.db or args.no_gcs:
        if args.db:
            os.environ["APPTRACK_DB_PATH"] = str(args.db)
        engine = get_engine(args.db)
        with get_session(engine) as session:
            results["promote"] = promote_to_review(session, args.min_score)
            results["queue"] = get_review_queue(session)
            results["summary"] = get_review_summary(session)
        engine.dispose()
    else:
        with gcs_managed_db() as engine:
            with get_session(engine) as session:
                results["promote"] = promote_to_review(session, args.min_score)
                results["queue"] = get_review_queue(session)
                results["summary"] = get_review_summary(session)

    # Save results
    os.makedirs("output", exist_ok=True)
    with open("output/apptrack_review_queue.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    promo = results["promote"]
    logger.info(f"✓ Promoted: {promo['promoted']} to review queue")

    if args.notify:
        _send_notification(results["queue"], results["summary"])


if __name__ == "__main__":
    main()
