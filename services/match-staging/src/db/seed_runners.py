"""Seed runner fleet data from GitLab API.

Populates the runners table with current fleet inventory and
captures an initial status snapshot.

Usage:
    python -m src.db.seed_runners [--db sqlite:///data/bewerbungen.db]
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Optional
from urllib.request import Request, urlopen

from sqlalchemy import select

from src.db.connection import init_db, get_session
from src.db.models import Runner, RunnerSnapshot, MABObservation


# --- Runner metadata (what the API doesn't tell us) ---

RUNNER_META = {
    "Mac Shell Runner":         {"executor": "shell",  "location": "mac1",      "cost": 0.0},
    "Mac Docker Runner":        {"executor": "docker", "location": "mac1",      "cost": 0.0},
    "Mac K8s Runner":           {"executor": "k8s",    "location": "mac1",      "cost": 0.0},
    "Mac2 Shell Runner":        {"executor": "shell",  "location": "mac2",      "cost": 0.0},
    "Mac2 Docker Runner":       {"executor": "docker", "location": "mac2",      "cost": 0.0},
    "Mac2 K8s Runner":          {"executor": "k8s",    "location": "mac2",      "cost": 0.0},
    "Linux Yoga Shell Runner":  {"executor": "shell",  "location": "yoga",      "cost": 0.0},
    "Linux Yoga Docker Runner": {"executor": "docker", "location": "yoga",      "cost": 0.0},
    "Linux Yoga K8s Runner":    {"executor": "k8s",    "location": "yoga",      "cost": 0.0},
    "gitlab-runner-nordic":     {"executor": "docker", "location": "gcp_nordic","cost": 0.02},
    "Nordic K8s Runner":        {"executor": "k8s",    "location": "gcp_nordic","cost": 0.02},
}


def fetch_runners_from_gitlab(
    pat: str,
    project_id: str = "77555895",
) -> list[dict]:
    """Fetch current runners from GitLab API."""
    req = Request(
        f"https://gitlab.com/api/v4/projects/{project_id}/runners?type=project_type&per_page=50",
        headers={"PRIVATE-TOKEN": pat},
    )
    with urlopen(req) as resp:
        return json.loads(resp.read())


async def seed_runners(pat: str, dry_run: bool = False) -> dict:
    """Seed runner fleet from GitLab API into the database."""
    engine = await init_db()
    stats = {"runners_added": 0, "snapshots_added": 0, "skipped": 0}

    # Fetch live data
    gl_runners = fetch_runners_from_gitlab(pat)
    print(f"Fetched {len(gl_runners)} runners from GitLab API")

    async with get_session() as session:
        for gl in gl_runners:
            name = gl["description"]
            gitlab_id = gl["id"]

            # Check if already exists
            existing = await session.execute(
                select(Runner).where(Runner.gitlab_runner_id == gitlab_id)
            )
            if existing.scalar_one_or_none():
                stats["skipped"] += 1
                print(f"  ⏭️  {name} (already in DB)")
                continue

            # Get metadata
            meta = RUNNER_META.get(name, {"executor": "docker", "location": "shared", "cost": 0.0})

            runner = Runner(
                gitlab_runner_id=gitlab_id,
                name=name,
                executor=meta["executor"],
                location=meta["location"],
                tags=gl.get("tag_list", []),
                cost_eur_h=meta["cost"],
                is_active=gl.get("active", True),
            )

            if not dry_run:
                session.add(runner)
                await session.flush()  # Get the ID

                # Add initial status snapshot
                snapshot = RunnerSnapshot(
                    runner_id=runner.id,
                    status=gl["status"],
                    ip_address=gl.get("ip_address"),
                )
                session.add(snapshot)
                stats["snapshots_added"] += 1

            stats["runners_added"] += 1
            print(f"  ✅ {name} ({meta['executor']}/{meta['location']}) → {gl['status']}")

        if not dry_run:
            await session.commit()

    return stats


async def main():
    pat = os.getenv("GITLAB_API_TOKEN", "")
    if not pat and len(sys.argv) > 1:
        pat = sys.argv[1]
    if not pat:
        print("Error: Set GITLAB_API_TOKEN or pass as argument")
        sys.exit(1)

    dry_run = "--dry-run" in sys.argv

    print(f"{'DRY RUN — ' if dry_run else ''}Seeding Runner Fleet")
    print("=" * 60)

    stats = await seed_runners(pat, dry_run=dry_run)

    print(f"\nRunners added:   {stats['runners_added']}")
    print(f"Snapshots added: {stats['snapshots_added']}")
    print(f"Skipped:         {stats['skipped']}")

    if not dry_run:
        print("\n✅ Runner fleet seeded into database")


if __name__ == "__main__":
    asyncio.run(main())
