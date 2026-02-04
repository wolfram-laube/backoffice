#!/usr/bin/env python3
"""
CLARISSA Timesheet Generator

Generates timesheets from GitLab Time Tracking data using GraphQL API.

The GraphQL API correctly returns the `spentAt` date, unlike the Notes API
which only shows the note creation date.

Usage:
    # Single consultant
    python generate_timesheet.py --client nemensis --period 2026-01 --consultant wolfram
    
    # All consultants for a client
    python generate_timesheet.py --client nemensis --period 2026-01 --all-consultants
    
Requirements:
    - GitLab issues must have label matching client's gitlab_label (e.g., "client:nemensis")
    - Time is tracked via /spend command on issues
    - GITLAB_TOKEN environment variable must be set
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Optional

try:
    import yaml
    import requests
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("   pip install pyyaml requests")
    sys.exit(1)

# Paths
SCRIPT_DIR = Path(__file__).parent
BILLING_DIR = SCRIPT_DIR.parent
CONFIG_DIR = BILLING_DIR / "config"
TEMPLATES_DIR = BILLING_DIR / "templates"
OUTPUT_DIR = BILLING_DIR / "output"

# GitLab API
GITLAB_GRAPHQL_URL = os.environ.get("GITLAB_GRAPHQL_URL", "https://gitlab.com/api/graphql")
GITLAB_PROJECT_PATH = os.environ.get("GITLAB_PROJECT_PATH", "wolfram_laube/blauweiss_llc/clarissa")
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN", "")


def load_config() -> dict:
    """Load client and consultant configuration."""
    config_file = CONFIG_DIR / "clients.yaml"
    if not config_file.exists():
        print(f"❌ Config not found: {config_file}")
        sys.exit(1)
    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_time_entries_graphql(
    project_path: str,
    year: int,
    month: int,
    gitlab_label: str,
    gitlab_username: Optional[str] = None
) -> dict:
    """
    Fetch time tracking entries from GitLab using GraphQL API.
    
    The GraphQL API correctly returns `spentAt` date, unlike the REST Notes API.
    
    Args:
        project_path: GitLab project path (e.g., "wolfram_laube/blauweiss_llc/clarissa")
        year: Year (e.g., 2026)
        month: Month (1-12)
        gitlab_label: Label to filter issues (e.g., "client:nemensis")
        gitlab_username: Optional - filter by who spent the time
    
    Returns:
        dict: {day: [(hours, description, issue_title), ...]}
    """
    if not GITLAB_TOKEN:
        print("❌ GITLAB_TOKEN environment variable not set")
        print("   Export your GitLab Personal Access Token:")
        print("   export GITLAB_TOKEN='glpat-xxx'")
        return {}
    
    headers = {
        "Authorization": f"Bearer {GITLAB_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Calculate date range
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    entries_by_day = defaultdict(list)
    
    # GraphQL query to fetch issues with timelogs
    query = """
    query($projectPath: ID!, $labelName: String!, $cursor: String) {
      project(fullPath: $projectPath) {
        issues(labelName: [$labelName], state: all, first: 50, after: $cursor) {
          pageInfo {
            hasNextPage
            endCursor
          }
          nodes {
            iid
            title
            timelogs {
              nodes {
                spentAt
                timeSpent
                user {
                  username
                }
              }
            }
          }
        }
      }
    }
    """
    
    print(f"   Fetching issues with label '{gitlab_label}' via GraphQL...")
    
    cursor = None
    total_issues = 0
    
    while True:
        variables = {
            "projectPath": project_path,
            "labelName": gitlab_label,
            "cursor": cursor
        }
        
        response = requests.post(
            GITLAB_GRAPHQL_URL,
            headers=headers,
            json={"query": query, "variables": variables}
        )
        
        if response.status_code != 200:
            print(f"❌ GraphQL error: {response.status_code}")
            print(f"   {response.text[:200]}")
            return {}
        
        data = response.json()
        
        if "errors" in data:
            print(f"❌ GraphQL query errors:")
            for error in data["errors"]:
                print(f"   {error.get('message', error)}")
            return {}
        
        project_data = data.get("data", {}).get("project")
        if not project_data:
            print(f"❌ Project not found: {project_path}")
            return {}
        
        issues_data = project_data.get("issues", {})
        issues = issues_data.get("nodes", [])
        total_issues += len(issues)
        
        for issue in issues:
            issue_title = issue.get("title", "")
            timelogs = issue.get("timelogs", {}).get("nodes", [])
            
            for timelog in timelogs:
                spent_at_str = timelog.get("spentAt")
                time_spent_seconds = timelog.get("timeSpent", 0)
                user = timelog.get("user", {})
                username = user.get("username", "")
                
                # Filter by username if specified
                if gitlab_username and username != gitlab_username:
                    continue
                
                if not spent_at_str:
                    continue
                
                # Parse date - format: "2026-01-03T17:02:13Z"
                try:
                    spent_at = datetime.fromisoformat(spent_at_str.replace("Z", "+00:00"))
                except ValueError:
                    continue
                
                # Check if within our target month
                spent_at_naive = spent_at.replace(tzinfo=None)
                if not (start_date <= spent_at_naive < end_date):
                    continue
                
                # Convert seconds to hours
                hours = time_spent_seconds / 3600
                
                # Skip negative entries (corrections) for display purposes
                # They're still included in the total calculation
                if hours == 0:
                    continue
                
                day = spent_at.day
                desc = issue_title[:50] + "..." if len(issue_title) > 50 else issue_title
                entries_by_day[day].append((hours, desc))
        
        # Pagination
        page_info = issues_data.get("pageInfo", {})
        if page_info.get("hasNextPage"):
            cursor = page_info.get("endCursor")
        else:
            break
    
    print(f"   Found {total_issues} issues")
    
    return dict(entries_by_day)


def consolidate_entries(entries: dict) -> dict:
    """
    Consolidate entries per day - sum hours and combine descriptions.
    Handles negative entries (time corrections).
    """
    consolidated = {}
    
    for day, day_entries in entries.items():
        total_hours = sum(h for h, _ in day_entries)
        
        # Skip days with zero or negative net time
        if total_hours <= 0:
            continue
        
        # Combine unique descriptions
        descriptions = list(set(d for _, d in day_entries if d))
        desc = "; ".join(descriptions[:2])
        if len(descriptions) > 2:
            desc += f" (+{len(descriptions)-2} more)"
        
        consolidated[day] = [(total_hours, desc)]
    
    return consolidated


def generate_timesheet_typ(
    year: int,
    month: int,
    client_id: str,
    client_config: dict,
    consultant_id: str,
    consultant_config: dict,
    entries: dict,
    lang: str = "de"
) -> str:
    """Generate Typst timesheet content."""
    
    # Build daily_entries string
    daily_entries_parts = []
    for day, day_entries in sorted(entries.items()):
        total_hours = sum(h for h, _ in day_entries)
        # Combine descriptions
        descriptions = list(set(d for _, d in day_entries))
        desc = "; ".join(descriptions[:2])
        if len(descriptions) > 2:
            desc += f" (+{len(descriptions)-2} more)"
        # Escape quotes in description
        desc = desc.replace('"', '\"')
        daily_entries_parts.append(f'    "{day}": ({total_hours:.2f}, "{desc}"),')
    
    daily_entries_str = "
".join(daily_entries_parts) if daily_entries_parts else "    // No entries"
    
    # Determine country from consultant or default
    country = "AT"  # Default
    
    # Get approver info
    approver = client_config.get("approver", {})
    approver_name = approver.get("name", "")
    approver_title = approver.get("title", "")
    
    content = f'''// BLAUWEISS Timesheet - {year}-{month:02d}
// Client: {client_config.get('name', '')}
// Consultant: {consultant_config.get('name', '')}
// Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}

#import "../templates/timesheet.typ": timesheet

#timesheet(
  year: {year},
  month: {month},
  client_name: "{client_config.get('name', '')}",
  client_short: "{client_config.get('short', '')}",
  project_name: "{client_config.get('contract_number', '')}",
  contract_number: "{client_config.get('contract_number', '')}",
  consultant_name: "{consultant_config.get('name', '')}",
  country: "{country}",
  lang: "{lang}",
  approver_name: "{approver_name}",
  approver_title: "{approver_title}",
  daily_entries: (
{daily_entries_str}
  ),
)
'''
    return content


def generate_timesheet(
    client_id: str,
    consultant_id: str,
    year: int,
    month: int,
    lang: str,
    config: dict
) -> Optional[Path]:
    """Generate a single timesheet for one consultant."""
    
    client_config = config["clients"][client_id]
    consultant_config = config["consultants"][consultant_id]
    
    gitlab_label = client_config.get("gitlab_label", f"client:{client_id}")
    gitlab_username = consultant_config.get("gitlab_username")
    
    print(f"
📋 Generating timesheet:")
    print(f"   Client: {client_config['name']}")
    print(f"   Consultant: {consultant_config['name']} (@{gitlab_username})")
    print(f"   Period: {year}-{month:02d}")
    
    # Fetch time entries via GraphQL
    entries = fetch_time_entries_graphql(
        GITLAB_PROJECT_PATH,
        year,
        month,
        gitlab_label,
        gitlab_username
    )
    
    if not entries:
        print("   ⚠️ No time entries found")
        return None
    
    # Consolidate entries per day
    entries = consolidate_entries(entries)
    
    if not entries:
        print("   ⚠️ No positive time entries after consolidation")
        return None
    
    # Calculate total
    total_hours = sum(sum(h for h, _ in day_entries) for day_entries in entries.values())
    print(f"   ✅ Found {total_hours:.1f} hours across {len(entries)} days")
    
    # Generate Typst content
    content = generate_timesheet_typ(
        year, month, client_id, client_config,
        consultant_id, consultant_config, entries, lang
    )
    
    # Write output file
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{consultant_id}_{client_id}_{year}-{month:02d}_timesheet.typ"
    output_file = OUTPUT_DIR / filename
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"   📄 Generated: {output_file.name}")
    
    # Also write sync metadata
    sync_data = {
        "client_id": client_id,
        "consultant_id": consultant_id,
        "year": year,
        "month": month,
        "lang": lang,
        "total_hours": total_hours,
        "entries": {str(k): v for k, v in entries.items()},
        "generated_at": datetime.now().isoformat(),
        "api_source": "graphql"  # Mark that this used GraphQL API
    }
    sync_file = output_file.with_suffix(".sync.json")
    with open(sync_file, "w", encoding="utf-8") as f:
        json.dump(sync_data, f, indent=2)
    
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Generate timesheets from GitLab time tracking (GraphQL API)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Single consultant
    %(prog)s --client nemensis --period 2026-01 --consultant wolfram
    
    # All consultants for a client
    %(prog)s --client nemensis --period 2026-01 --all-consultants
    
Environment:
    GITLAB_TOKEN        GitLab Personal Access Token (required)
    GITLAB_PROJECT_PATH Project path (default: wolfram_laube/blauweiss_llc/clarissa)
"""
    )
    parser.add_argument("--client", "-c", required=True, help="Client ID from clients.yaml")
    parser.add_argument("--period", "-p", required=True, help="Period as YYYY-MM")
    parser.add_argument("--consultant", help="Consultant ID (from clients.yaml consultants)")
    parser.add_argument("--all-consultants", action="store_true", help="Generate for all consultants")
    parser.add_argument("--lang", "-l", default="de", help="Language (de, en, vi, ar, is)")
    
    args = parser.parse_args()
    
    # Parse period
    try:
        year, month = map(int, args.period.split("-"))
    except ValueError:
        print(f"❌ Invalid period format: {args.period}")
        print("   Use YYYY-MM (e.g., 2026-01)")
        sys.exit(1)
    
    # Load config
    config = load_config()
    
    # Validate client
    if args.client not in config.get("clients", {}):
        print(f"❌ Unknown client: {args.client}")
        available = [k for k in config.get("clients", {}).keys() if not k.startswith("_")]
        print(f"   Available: {', '.join(available)}")
        sys.exit(1)
    
    client_config = config["clients"][args.client]
    
    # Determine which consultants to process
    if args.all_consultants:
        consultant_ids = client_config.get("consultants", [])
        if not consultant_ids:
            print(f"❌ No consultants configured for client '{args.client}'")
            sys.exit(1)
        print(f"🔄 Generating timesheets for {len(consultant_ids)} consultants...")
    elif args.consultant:
        if args.consultant not in config.get("consultants", {}):
            print(f"❌ Unknown consultant: {args.consultant}")
            available = list(config.get("consultants", {}).keys())
            print(f"   Available: {', '.join(available)}")
            sys.exit(1)
        consultant_ids = [args.consultant]
    else:
        print("❌ Specify --consultant or --all-consultants")
        sys.exit(1)
    
    # Generate timesheets
    generated = []
    for consultant_id in consultant_ids:
        result = generate_timesheet(
            args.client,
            consultant_id,
            year,
            month,
            args.lang,
            config
        )
        if result:
            generated.append(result)
    
    # Summary
    print(f"
{'='*50}")
    print(f"✅ Generated {len(generated)} timesheet(s)")
    for f in generated:
        print(f"   📄 {f.name}")
    
    if generated:
        print(f"
Next steps:")
        print(f"   1. Review and get approvals")
        print(f"   2. Generate invoice:")
        print(f"      python generate_invoice.py --client {args.client} --period {args.period}")


if __name__ == "__main__":
    main()
