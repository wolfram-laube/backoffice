#!/usr/bin/env python3
"""
Applications Pipeline - Stage Job
Bridges match output → Vorhölle (Match Staging Service).

Reads output/matches.json and stages high-scoring matches as GitLab Issues
with structured labels, notifications, and review workflow.

Modes:
  1. SERVICE mode: POST to running Vorhölle service (STAGING_SERVICE_URL)
  2. DIRECT mode:  Create GitLab Issues directly via API (default fallback)
"""

import json
import os
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
#  Config
# ---------------------------------------------------------------------------

GITLAB_TOKEN = os.environ.get(
    "GITLAB_PRIVATE_TOKEN",
    os.environ.get("CI_JOB_TOKEN", ""),
)
PROJECT_ID = os.environ.get("CI_PROJECT_ID", "77555895")
GITLAB_API = os.environ.get("GITLAB_API_URL", "https://gitlab.com/api/v4")
STAGING_URL = os.environ.get("STAGING_SERVICE_URL", "")  # e.g. https://match-staging-....run.app
MIN_SCORE = int(os.environ.get("STAGING_MIN_SCORE", "70"))
PROFILE_NAME = os.environ.get("STAGING_PROFILE", "wolfram")
ASSIGNEE_ID = int(os.environ.get("STAGING_ASSIGNEE_ID", "1349601"))
LABELS_PREFIX = "job-match"
MAX_STAGE = int(os.environ.get("MAX_STAGE", "10"))
DRY_RUN = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")

import requests  # noqa: E402 (after config so we fail fast on missing env)

# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------


def load_matches(path="output/matches.json"):
    """Load matches.json from the match stage."""
    with open(path) as f:
        data = json.load(f)

    profile = data.get("profiles", {}).get(PROFILE_NAME, {})
    top = profile.get("top", [])

    # Filter by min score
    qualified = [m for m in top if m.get("score", 0) >= MIN_SCORE]
    qualified.sort(key=lambda m: -m["score"])

    print(f"📊 Profile '{PROFILE_NAME}': {len(top)} matches, {len(qualified)} ≥ {MIN_SCORE}%")
    return qualified[:MAX_STAGE]


def match_to_job_match(m):
    """Transform pipeline match dict → Vorhölle JobMatch dict."""
    project = m.get("project", {})
    return {
        "title": project.get("title", "Unknown"),
        "provider": project.get("company", project.get("provider", "—")),
        "contact_email": project.get("contact_email"),
        "contact_name": project.get("contact_name"),
        "location": project.get("location", "Remote"),
        "remote_percentage": project.get("remote_percent"),
        "start_date": project.get("start_date", "ASAP"),
        "duration": project.get("duration", "—"),
        "rate_eur": 105,
        "source_url": project.get("url"),
        "source_platform": "freelancermap",
        "overall_score": m.get("score", 0),
        "strengths": [f"Keyword: {kw}" for kw in m.get("keywords", [])],
        "gaps": [],
        "notes": f"AI project: {m.get('is_ai', False)}",
    }


# ---------------------------------------------------------------------------
#  Mode 1: Via Vorhölle Service API
# ---------------------------------------------------------------------------


def stage_via_service(matches):
    """POST matches to running staging service."""
    cycle_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "cycle_id": cycle_id,
        "matches": [match_to_job_match(m) for m in matches],
        "attach_profile": True,
        "attach_cv": False,
        "auto_notify": True,
    }

    print(f"\n🚀 POST {STAGING_URL}/api/v1/matches ({len(matches)} matches)")
    resp = requests.post(
        f"{STAGING_URL}/api/v1/matches",
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()

    staged = result.get("staged", [])
    errors = result.get("errors", [])
    notified = result.get("notifications_sent", [])

    print(f"✅ Staged: {len(staged)} | Errors: {len(errors)} | Notified: {notified}")
    for s in staged:
        m = s["match"]
        print(f"   #{s['gitlab_issue_iid']} [{m['overall_score']}%] {m['title']}")
    for e in errors:
        print(f"   ❌ {e}")

    return result


# ---------------------------------------------------------------------------
#  Mode 2: Direct GitLab API (no service running)
# ---------------------------------------------------------------------------


def _score_tier(score):
    return "high" if score >= 90 else "medium"


def _score_emoji(score):
    return "🔥" if score >= 90 else "✅"


def _build_description(jm, cycle_id):
    """Build structured issue description (mirrors GitLabAdapter)."""
    lines = [
        "## Match Details",
        f"- **Score:** {_score_emoji(jm['overall_score'])} {jm['overall_score']}%",
        f"- **Provider:** {jm['provider']}",
        f"- **Contact:** {jm.get('contact_name') or '—'} ({jm.get('contact_email') or '—'})",
        f"- **Location:** {jm['location']}"
        + (f" ({jm['remote_percentage']}% Remote)" if jm.get("remote_percentage") else ""),
        f"- **Start:** {jm['start_date']} | **Duration:** {jm['duration']}",
        f"- **Rate:** {jm['rate_eur']} EUR/h",
    ]
    if jm.get("source_url"):
        lines.append(f"- **Source:** [{jm.get('source_platform', 'Link')}]({jm['source_url']})")
    else:
        lines.append(f"- **Source:** {jm.get('source_platform', '—')}")
    lines.append(f"- **Cycle:** `{cycle_id}`")
    lines.append("")

    if jm.get("strengths"):
        lines.append("## Strengths")
        for s in jm["strengths"]:
            lines.append(f"- ✅ {s}")
        lines.append("")

    if jm.get("gaps"):
        lines.append("## Gaps")
        for g in jm["gaps"]:
            lines.append(f"- ⚠️ {g}")
        lines.append("")

    if jm.get("notes"):
        lines.append(f"> {jm['notes']}")

    return "\n".join(lines)


def stage_direct(matches):
    """Create GitLab Issues directly via API."""
    cycle_id = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    staged = []
    errors = []

    for m in matches:
        jm = match_to_job_match(m)
        score = jm["overall_score"]
        title = f"[JOB-MATCH] {score}% — {jm['title']}"
        labels = f"{LABELS_PREFIX},{LABELS_PREFIX}/pending,match-score/{_score_tier(score)}"

        if DRY_RUN:
            print(f"   🏜️ [DRY] {title}")
            staged.append({"title": title, "score": score, "dry_run": True})
            continue

        description = _build_description(jm, cycle_id)

        # Check for duplicate (same title, still pending)
        check = requests.get(
            f"{GITLAB_API}/projects/{PROJECT_ID}/issues",
            headers=headers,
            params={
                "labels": f"{LABELS_PREFIX}/pending",
                "search": jm["title"][:40],
                "state": "opened",
                "per_page": 5,
            },
        )
        if check.ok:
            dupes = [i for i in check.json() if jm["title"][:30] in i.get("title", "")]
            if dupes:
                print(f"   ⏭️ Duplicate: #{dupes[0]['iid']} {jm['title'][:40]}")
                continue

        resp = requests.post(
            f"{GITLAB_API}/projects/{PROJECT_ID}/issues",
            headers=headers,
            json={
                "title": title,
                "description": description,
                "labels": labels,
                "assignee_id": ASSIGNEE_ID,
            },
        )

        if resp.ok:
            issue = resp.json()
            print(f"   ✅ #{issue['iid']} [{score}%] {jm['title'][:45]}")
            staged.append({
                "gitlab_issue_iid": issue["iid"],
                "gitlab_issue_id": issue["id"],
                "gitlab_issue_url": issue["web_url"],
                "score": score,
                "title": jm["title"],
            })
        else:
            err = f"Failed to create issue for '{jm['title']}': {resp.status_code} {resp.text[:100]}"
            print(f"   ❌ {err}")
            errors.append(err)

    return {
        "cycle_id": cycle_id,
        "mode": "dry_run" if DRY_RUN else "direct",
        "staged": staged,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------


def main():
    print("=" * 70)
    print("🚪 VORHÖLLE — Match Staging Pipeline Job")
    print("=" * 70)

    if not os.path.exists("output/matches.json"):
        print("❌ output/matches.json not found. Run applications:match first.")
        sys.exit(1)

    matches = load_matches()
    if not matches:
        print("ℹ️ No matches above threshold. Nothing to stage.")
        sys.exit(0)

    # Choose mode
    if STAGING_URL:
        print(f"\n🌐 Mode: SERVICE ({STAGING_URL})")
        result = stage_via_service(matches)
    else:
        if not GITLAB_TOKEN:
            print("❌ No GITLAB_PRIVATE_TOKEN and no STAGING_SERVICE_URL. Cannot stage.")
            sys.exit(1)
        mode = "DRY RUN" if DRY_RUN else "DIRECT (GitLab API)"
        print(f"\n📋 Mode: {mode}")
        result = stage_direct(matches)

    # Save output
    os.makedirs("output", exist_ok=True)
    with open("output/staged.json", "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)

    staged_count = len(result.get("staged", []))
    error_count = len(result.get("errors", []))

    print(f"\n{'=' * 70}")
    print(f"📊 Result: {staged_count} staged, {error_count} errors")
    print(f"   Saved: output/staged.json")
    print(f"   Review: https://gitlab.com/wolfram_laube/blauweiss_llc/ops/backoffice/-/issues?label_name[]=job-match%2Fpending")
    print(f"{'=' * 70}")

    if error_count > 0 and staged_count == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
