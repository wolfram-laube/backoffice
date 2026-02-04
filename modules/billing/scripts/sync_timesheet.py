#!/usr/bin/env python3
"""
CLARISSA Timesheet Sync

Syncs timesheet changes back to GitLab.

Compares the edited .typ file against the original GitLab data
and posts corrections to a dedicated "Timesheet Corrections" issue.

Usage:
    python sync_timesheet.py billing/output/2026-01_timesheet_nemensis_de.typ
    python sync_timesheet.py 2026-01_timesheet_nemensis_de.typ --dry-run
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

# Paths
SCRIPT_DIR = Path(__file__).parent
BILLING_DIR = SCRIPT_DIR.parent
CONFIG_DIR = BILLING_DIR / "config"
OUTPUT_DIR = BILLING_DIR / "output"

# GitLab API
GITLAB_API_URL = os.environ.get("GITLAB_API_URL", "https://gitlab.com/api/v4")
GITLAB_PROJECT_ID = os.environ.get("GITLAB_PROJECT_ID", "77260390")
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN", "")


def load_config() -> dict:
    """Load client configuration."""
    config_file = CONFIG_DIR / "clients.yaml"
    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_timesheet_typ(typ_file: Path) -> dict:
    """
    Parse a timesheet .typ file and extract daily entries.
    
    Returns: {day: {"hours": float, "description": str}, ...}
    """
    with open(typ_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Find daily_entries block
    match = re.search(r'daily_entries:\s*\((.*?)\)\s*,?\s*\)', content, re.DOTALL)
    if not match:
        print("❌ Could not find daily_entries in timesheet")
        return {}
    
    entries_block = match.group(1)
    
    # Parse individual entries: "5": (8, "Description"),
    entries = {}
    for entry_match in re.finditer(r'"(\d+)":\s*\((\d+(?:\.\d+)?),\s*"([^"]*)"\)', entries_block):
        day = int(entry_match.group(1))
        hours = float(entry_match.group(2))
        description = entry_match.group(3)
        entries[day] = {"hours": hours, "description": description}
    
    return entries


def load_sync_data(typ_file: Path) -> dict:
    """Load the original GitLab sync data."""
    sync_file = typ_file.with_suffix(".sync.json")
    
    if not sync_file.exists():
        print(f"❌ Sync file not found: {sync_file}")
        print("   Was this timesheet generated with generate_timesheet.py?")
        return None
    
    with open(sync_file, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_diff(original: dict, current: dict) -> list:
    """
    Calculate differences between original GitLab data and current timesheet.
    
    Returns list of diffs: [{"day": 5, "delta": 2.0, "description": "...", "action": "add"}, ...]
    """
    diffs = []
    
    # Get all days from both
    all_days = set(original.keys()) | set(current.keys())
    
    for day_str in all_days:
        day = int(day_str) if isinstance(day_str, str) else day_str
        day_str = str(day)
        
        orig_data = original.get(day_str, {})
        curr_data = current.get(day, {})
        
        orig_hours = orig_data.get("hours", 0) if orig_data else 0
        curr_hours = curr_data.get("hours", 0) if curr_data else 0
        
        delta = curr_hours - orig_hours
        
        if abs(delta) > 0.01:  # Significant difference
            description = curr_data.get("description", "") if curr_data else orig_data.get("description", "")
            
            if delta > 0:
                action = "nachgetragen" if orig_hours == 0 else "Korrektur"
            else:
                action = "storniert" if curr_hours == 0 else "Korrektur"
            
            diffs.append({
                "day": day,
                "delta": delta,
                "original": orig_hours,
                "current": curr_hours,
                "description": description,
                "action": action,
            })
    
    return sorted(diffs, key=lambda x: x["day"])


def find_or_create_correction_issue(project_id: str, year: int, month: int, client_name: str) -> int:
    """Find or create the timesheet corrections issue for this month."""
    try:
        import requests
    except ImportError:
        print("❌ 'requests' not installed")
        return None
    
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    
    # Search for existing issue
    issue_title = f"⏱️ Timesheet Corrections {year}-{month:02d} [{client_name}]"
    
    search_url = f"{GITLAB_API_URL}/projects/{project_id}/issues"
    params = {"search": f"Timesheet Corrections {year}-{month:02d}", "state": "opened"}
    
    response = requests.get(search_url, headers=headers, params=params)
    if response.status_code == 200:
        issues = response.json()
        for issue in issues:
            if client_name in issue["title"] and f"{year}-{month:02d}" in issue["title"]:
                print(f"📌 Found existing issue: #{issue['iid']}")
                return issue["iid"]
    
    # Create new issue
    create_url = f"{GITLAB_API_URL}/projects/{project_id}/issues"
    data = {
        "title": issue_title,
        "description": f"""Timesheet corrections for {year}-{month:02d}

**Client:** {client_name}
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

This issue tracks time corrections made after the initial timesheet generation.
Each `/spend` note below represents a correction from the reviewed timesheet.

---
""",
        "labels": "billing,timesheet-correction",
    }
    
    response = requests.post(create_url, headers=headers, json=data)
    if response.status_code == 201:
        issue = response.json()
        print(f"✅ Created correction issue: #{issue['iid']}")
        return issue["iid"]
    else:
        print(f"❌ Failed to create issue: {response.status_code}")
        print(response.text)
        return None


def post_time_correction(project_id: str, issue_iid: int, year: int, month: int, diff: dict) -> bool:
    """Post a /spend note to the correction issue."""
    try:
        import requests
    except ImportError:
        return False
    
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    
    day = diff["day"]
    delta = diff["delta"]
    description = diff["description"]
    action = diff["action"]
    
    # Format the date
    date_str = f"{year}-{month:02d}-{day:02d}"
    
    # Build the spend command
    if delta > 0:
        spend_cmd = f"/spend {delta:.1f}h {date_str}"
    else:
        spend_cmd = f"/spend {delta:.1f}h {date_str}"  # GitLab accepts negative
    
    # Create note body
    note_body = f"""{spend_cmd}

**{action}:** {description}
- Original: {diff['original']:.1f}h
- Korrigiert: {diff['current']:.1f}h
- Differenz: {delta:+.1f}h
"""
    
    url = f"{GITLAB_API_URL}/projects/{project_id}/issues/{issue_iid}/notes"
    data = {"body": note_body}
    
    response = requests.post(url, headers=headers, json=data)
    
    return response.status_code == 201


def update_sync_file(typ_file: Path, current_entries: dict):
    """Update the sync file with current state after successful sync."""
    sync_file = typ_file.with_suffix(".sync.json")
    
    with open(sync_file, "r", encoding="utf-8") as f:
        sync_data = json.load(f)
    
    # Update gitlab_entries with current state
    sync_data["gitlab_entries"] = {
        str(k): {"hours": v["hours"], "description": v["description"], "entries": []}
        for k, v in current_entries.items()
    }
    sync_data["last_synced"] = datetime.now().isoformat()
    
    with open(sync_file, "w", encoding="utf-8") as f:
        json.dump(sync_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Updated sync file: {sync_file}")


def main():
    parser = argparse.ArgumentParser(description="Sync timesheet changes to GitLab")
    parser.add_argument("timesheet", help="Path to timesheet .typ file")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without syncing")
    parser.add_argument("--force", action="store_true", help="Sync even if no changes detected")
    
    args = parser.parse_args()
    
    # Find timesheet file
    typ_file = Path(args.timesheet)
    if not typ_file.exists():
        # Try in output directory
        typ_file = OUTPUT_DIR / args.timesheet
    
    if not typ_file.exists():
        print(f"❌ Timesheet not found: {args.timesheet}")
        sys.exit(1)
    
    print(f"📄 Parsing timesheet: {typ_file}")
    
    # Load sync data
    sync_data = load_sync_data(typ_file)
    if not sync_data:
        sys.exit(1)
    
    year = sync_data["year"]
    month = sync_data["month"]
    client_id = sync_data["client_id"]
    original_entries = sync_data.get("gitlab_entries", {})
    
    # Load config for client name
    config = load_config()
    client_config = config["clients"].get(client_id, {})
    client_name = client_config.get("short", client_id)
    
    # Parse current timesheet
    current_entries = parse_timesheet_typ(typ_file)
    
    print(f"
📊 Period: {year}-{month:02d}")
    print(f"👤 Client: {client_name}")
    print(f"📝 Original entries: {len(original_entries)}")
    print(f"📝 Current entries: {len(current_entries)}")
    
    # Calculate differences
    diffs = calculate_diff(original_entries, current_entries)
    
    if not diffs:
        print("
✅ No changes detected - timesheet matches GitLab")
        if not args.force:
            return
        print("   (--force specified, continuing anyway)")
    
    # Show differences
    print(f"
📋 Changes detected: {len(diffs)}")
    total_delta = 0
    for diff in diffs:
        delta_str = f"{diff['delta']:+.1f}h"
        print(f"   Tag {diff['day']:2d}: {delta_str:>7}  ({diff['action']}) {diff['description'][:40]}")
        total_delta += diff["delta"]
    
    print(f"
   Total Δ: {total_delta:+.1f}h")
    
    if args.dry_run:
        print("
⚠️ Dry run - no changes made to GitLab")
        return
    
    if not GITLAB_TOKEN:
        print("
❌ GITLAB_TOKEN not set - cannot sync to GitLab")
        sys.exit(1)
    
    # Find or create correction issue
    print("
🔄 Syncing to GitLab...")
    issue_iid = find_or_create_correction_issue(GITLAB_PROJECT_ID, year, month, client_name)
    
    if not issue_iid:
        print("❌ Could not get correction issue")
        sys.exit(1)
    
    # Post corrections
    success_count = 0
    for diff in diffs:
        if post_time_correction(GITLAB_PROJECT_ID, issue_iid, year, month, diff):
            print(f"   ✅ Tag {diff['day']}: {diff['delta']:+.1f}h")
            success_count += 1
        else:
            print(f"   ❌ Tag {diff['day']}: Failed to post")
    
    print(f"
✅ Synced {success_count}/{len(diffs)} corrections")
    
    # Update sync file
    if success_count == len(diffs):
        update_sync_file(typ_file, current_entries)
    
    print(f"
🔗 View corrections: https://gitlab.com/wolfram_laube/blauweiss_llc/clarissa/-/issues/{issue_iid}")


if __name__ == "__main__":
    main()
