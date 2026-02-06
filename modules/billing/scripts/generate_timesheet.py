#!/usr/bin/env python3
"""
BLAUWEISS Multi-Repo Timesheet Generator

Generates timesheets from GitLab Time Tracking data across multiple projects.
Uses GraphQL API to correctly fetch `spentAt` dates.

Usage:
    # Single consultant
    python generate_timesheet.py --client nemensis --period 2026-01 --consultant wolfram
    
    # All consultants for a client
    python generate_timesheet.py --client nemensis --period 2026-01 --all-consultants

Changes from v1:
    - Multi-repo support: queries all projects in config
    - Project grouping: groups time by project:: label
    - Per-client consultant rates
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Optional, List, Dict

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
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN", "")


def load_config() -> dict:
    """Load client and consultant configuration."""
    config_file = CONFIG_DIR / "clients.yaml"
    if not config_file.exists():
        print(f"❌ Config not found: {config_file}")
        sys.exit(1)
    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_time_entries_multi_repo(
    projects: List[str],
    year: int,
    month: int,
    gitlab_label: str,
    gitlab_username: Optional[str] = None
) -> Dict[str, List[tuple]]:
    """
    Fetch time tracking entries from multiple GitLab projects.
    
    Args:
        projects: List of project paths
        year: Year (e.g., 2026)
        month: Month (1-12)
        gitlab_label: Label to filter issues (e.g., "client::nemensis")
        gitlab_username: Optional - filter by who spent the time
    
    Returns:
        dict: {project_name: {day: [(hours, description, issue_title), ...]}}
    """
    if not GITLAB_TOKEN:
        print("❌ GITLAB_TOKEN environment variable not set")
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
    
    all_entries = defaultdict(lambda: defaultdict(list))  # {project: {day: [entries]}}
    
    # GraphQL query - also fetch labels to detect project
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
            labels {
              nodes {
                title
              }
            }
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
    
    for project_path in projects:
        project_name = project_path.split("/")[-1]  # e.g., "clarissa"
        print(f"   📂 Scanning {project_path}...")
        
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
                print(f"      ⚠️ Error: {response.status_code}")
                break
            
            data = response.json()
            
            if "errors" in data:
                print(f"      ⚠️ GraphQL error: {data['errors'][0].get('message', '')}")
                break
            
            project_data = data.get("data", {}).get("project")
            if not project_data:
                break
            
            issues_data = project_data.get("issues", {})
            issues = issues_data.get("nodes", [])
            total_issues += len(issues)
            
            for issue in issues:
                issue_title = issue.get("title", "")
                
                # Detect project from labels (project::clarissa, project::magnus, etc.)
                labels = [l.get("title", "") for l in issue.get("labels", {}).get("nodes", [])]
                detected_project = None
                for label in labels:
                    if label.startswith("project::"):
                        detected_project = label.replace("project::", "")
                        break
                
                # Use detected project or fall back to repo name
                entry_project = detected_project or project_name
                
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
                    
                    # Parse date
                    try:
                        spent_at = datetime.fromisoformat(spent_at_str.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                    
                    # Check if within target month
                    spent_at_naive = spent_at.replace(tzinfo=None)
                    if not (start_date <= spent_at_naive < end_date):
                        continue
                    
                    # Convert seconds to hours
                    hours = time_spent_seconds / 3600.0
                    day = spent_at_naive.day
                    
                    all_entries[entry_project][day].append((hours, issue_title, username))
            
            # Check pagination
            page_info = issues_data.get("pageInfo", {})
            if page_info.get("hasNextPage"):
                cursor = page_info.get("endCursor")
            else:
                break
        
        if total_issues > 0:
            print(f"      ✅ Found {total_issues} issues")
    
    return dict(all_entries)


def generate_timesheet(
    client_id: str,
    consultant_id: str,
    year: int,
    month: int,
    lang: str,
    config: dict
) -> Optional[Path]:
    """Generate timesheet for a consultant, grouped by project."""
    
    client_config = config["clients"][client_id]
    consultant_config = config["consultants"].get(consultant_id, {})
    
    # Get consultant's GitLab username
    gitlab_username = consultant_config.get("gitlab_username")
    if not gitlab_username:
        print(f"   ⚠️ No gitlab_username for consultant '{consultant_id}'")
        return None
    
    # Get rate (client-specific or default)
    client_consultant_config = client_config.get("consultants", {}).get(consultant_id, {})
    rate = client_consultant_config.get("rate") or consultant_config.get("default_rate", 100)
    
    print(f"\n📋 {consultant_config.get('name', consultant_id)} @ {client_config['name']}")
    print(f"   Rate: {rate} {client_config.get('currency', 'EUR')}/h")
    
    # Get projects list
    projects = config.get("projects", [])
    if not projects:
        print("   ⚠️ No projects configured in clients.yaml")
        return None
    
    # Fetch time entries from all projects
    entries_by_project = fetch_time_entries_multi_repo(
        projects,
        year,
        month,
        client_config.get("gitlab_label", f"client::{client_id}"),
        gitlab_username
    )
    
    if not entries_by_project:
        print(f"   ⚠️ No time entries found")
        return None
    
    # Calculate totals
    total_hours = 0
    project_hours = defaultdict(float)
    
    for project, days in entries_by_project.items():
        for day, entries in days.items():
            for hours, _, _ in entries:
                total_hours += hours
                project_hours[project] += hours
    
    if total_hours == 0:
        print(f"   ⚠️ No time entries for this consultant")
        return None
    
    # Print summary
    print(f"\n   Summary:")
    for project, hours in sorted(project_hours.items()):
        print(f"      {project}: {hours:.1f}h")
    print(f"      ────────────")
    print(f"      Total: {total_hours:.1f}h × {rate} = {total_hours * rate:.2f} {client_config.get('currency', 'EUR')}")
    
    # Generate output file (simplified - just JSON for now)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    period_str = f"{year}-{month:02d}"
    output_file = OUTPUT_DIR / f"timesheet_{client_id}_{consultant_id}_{period_str}.json"
    
    output_data = {
        "client": client_id,
        "consultant": consultant_id,
        "period": period_str,
        "rate": rate,
        "currency": client_config.get("currency", "EUR"),
        "total_hours": total_hours,
        "total_amount": total_hours * rate,
        "by_project": dict(project_hours),
        "entries": {proj: {day: [(h, d) for h, d, _ in e] 
                          for day, e in days.items()} 
                   for proj, days in entries_by_project.items()}
    }
    
    with open(output_file, "w") as f:
        json.dump(output_data, f, indent=2)
    
    print(f"   📄 {output_file.name}")
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Generate timesheets from GitLab time tracking (multi-repo)")
    parser.add_argument("--client", "-c", required=True, help="Client ID from clients.yaml")
    parser.add_argument("--period", "-p", required=True, help="Period as YYYY-MM")
    parser.add_argument("--consultant", help="Consultant ID")
    parser.add_argument("--all-consultants", action="store_true", help="Generate for all consultants")
    parser.add_argument("--lang", "-l", default="de", help="Language (de, en)")
    
    args = parser.parse_args()
    
    # Parse period
    try:
        year, month = map(int, args.period.split("-"))
    except ValueError:
        print(f"❌ Invalid period format: {args.period}")
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
    
    # Determine consultants
    if args.all_consultants:
        consultant_ids = list(client_config.get("consultants", {}).keys())
    elif args.consultant:
        consultant_ids = [args.consultant]
    else:
        print("❌ Specify --consultant or --all-consultants")
        sys.exit(1)
    
    print(f"🧾 Generating timesheets for {args.client} ({args.period})")
    
    # Generate timesheets
    generated = []
    for consultant_id in consultant_ids:
        result = generate_timesheet(args.client, consultant_id, year, month, args.lang, config)
        if result:
            generated.append(result)
    
    # Summary
    print(f"\n{'='*50}")
    print(f"✅ Generated {len(generated)} timesheet(s)")


if __name__ == "__main__":
    main()
