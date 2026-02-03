#!/usr/bin/env python3
"""
CRM Smart Automation - Follow-ups, Ghost Detection, Alerts

Automated CRM maintenance tasks:
- Follow-up reminders after X days without response
- Ghost detection for stale issues
- Hot lead alerts on status changes
- Duplicate detection for new issues

Required env:
  - GITLAB_TOKEN
  - CRM_PROJECT_ID (default: 78171527)

Optional env:
  - FOLLOW_UP_DAYS: Days before follow-up reminder (default: 7)
  - GHOST_DAYS: Days before ghost label (default: 30)
  - DRY_RUN: "true" for no changes
  - SEND_ALERTS: "true" to send email alerts
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from difflib import SequenceMatcher

# Config
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN") or os.environ.get("GITLAB_API_TOKEN")
CRM_PROJECT_ID = os.environ.get("CRM_PROJECT_ID", "78171527")
GITLAB_API = "https://gitlab.com/api/v4"

FOLLOW_UP_DAYS = int(os.environ.get("FOLLOW_UP_DAYS", "7"))
GHOST_DAYS = int(os.environ.get("GHOST_DAYS", "30"))
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"
SEND_ALERTS = os.environ.get("SEND_ALERTS", "false").lower() == "true"


def api_request(method: str, endpoint: str, data: Optional[dict] = None) -> Any:
    """Make GitLab API request."""
    url = f"{GITLAB_API}{endpoint}"
    headers = {
        "PRIVATE-TOKEN": GITLAB_TOKEN,
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, method=method, headers=headers, data=body)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  ⚠️ API Error {e.code}: {e.read().decode()[:200]}")
        return None


def fetch_all_issues(state: str = "opened") -> List[Dict]:
    """Fetch all CRM issues with pagination."""
    all_issues = []
    page = 1
    
    while True:
        endpoint = f"/projects/{CRM_PROJECT_ID}/issues?state={state}&per_page=100&page={page}"
        issues = api_request("GET", endpoint)
        
        if not issues:
            break
        
        for issue in issues:
            labels = [l.get("name", l) if isinstance(l, dict) else l for l in issue.get("labels", [])]
            if "epic" not in labels and "infrastructure" not in labels:
                issue["_labels"] = labels
                all_issues.append(issue)
        
        if len(issues) < 100:
            break
        page += 1
    
    return all_issues


def parse_date(date_str: str) -> datetime:
    """Parse ISO date string to datetime."""
    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))


def get_status(issue: Dict) -> str:
    """Get status from labels."""
    for label in issue.get("_labels", []):
        if label.startswith("status::"):
            return label
    return "status::unknown"


def add_label(issue_iid: int, label: str) -> bool:
    """Add label to issue."""
    if DRY_RUN:
        print(f"    [DRY RUN] Would add label '{label}'")
        return True
    
    endpoint = f"/projects/{CRM_PROJECT_ID}/issues/{issue_iid}"
    result = api_request("PUT", endpoint, {"add_labels": label})
    return result is not None


def add_comment(issue_iid: int, body: str) -> bool:
    """Add comment to issue."""
    if DRY_RUN:
        print(f"    [DRY RUN] Would add comment")
        return True
    
    endpoint = f"/projects/{CRM_PROJECT_ID}/issues/{issue_iid}/notes"
    result = api_request("POST", endpoint, {"body": body})
    return result is not None


def get_last_activity(issue: Dict) -> Tuple[datetime, str]:
    """Get last activity date and type for an issue."""
    updated = parse_date(issue["updated_at"])
    
    # Check for recent comments
    endpoint = f"/projects/{CRM_PROJECT_ID}/issues/{issue['iid']}/notes?per_page=1&sort=desc"
    notes = api_request("GET", endpoint)
    
    if notes and len(notes) > 0:
        note_date = parse_date(notes[0]["created_at"])
        if note_date > updated:
            return note_date, "comment"
    
    return updated, "update"


def check_follow_ups(issues: List[Dict]) -> List[Dict]:
    """Find issues needing follow-up reminders."""
    now = datetime.now().astimezone()
    cutoff = now - timedelta(days=FOLLOW_UP_DAYS)
    
    needs_followup = []
    
    # Only check "versendet" or "beim-kunden" status
    eligible_statuses = ["status::versendet", "status::beim-kunden"]
    
    for issue in issues:
        status = get_status(issue)
        if status not in eligible_statuses:
            continue
        
        # Skip if already has follow-up label
        if "needs-followup" in issue.get("_labels", []):
            continue
        
        last_activity, activity_type = get_last_activity(issue)
        
        if last_activity.replace(tzinfo=None) < cutoff.replace(tzinfo=None):
            days_since = (now.replace(tzinfo=None) - last_activity.replace(tzinfo=None)).days
            needs_followup.append({
                "issue": issue,
                "days_since": days_since,
                "last_activity": last_activity,
            })
    
    return needs_followup


def check_ghosts(issues: List[Dict]) -> List[Dict]:
    """Find issues that should be marked as ghost."""
    now = datetime.now().astimezone()
    cutoff = now - timedelta(days=GHOST_DAYS)
    
    ghosts = []
    
    # Only check active statuses
    active_statuses = ["status::versendet", "status::beim-kunden"]
    
    for issue in issues:
        status = get_status(issue)
        if status not in active_statuses:
            continue
        
        # Skip if already ghost
        if "status::ghost" in issue.get("_labels", []):
            continue
        
        last_activity, _ = get_last_activity(issue)
        
        if last_activity.replace(tzinfo=None) < cutoff.replace(tzinfo=None):
            days_since = (now.replace(tzinfo=None) - last_activity.replace(tzinfo=None)).days
            ghosts.append({
                "issue": issue,
                "days_since": days_since,
            })
    
    return ghosts


def check_hot_leads(issues: List[Dict]) -> List[Dict]:
    """Find hot leads that need attention."""
    hot_leads = []
    
    for issue in issues:
        if "hot-lead" not in issue.get("_labels", []):
            continue
        
        status = get_status(issue)
        
        # Alert for interview/verhandlung status
        if status in ["status::interview", "status::verhandlung"]:
            hot_leads.append({
                "issue": issue,
                "status": status,
                "priority": "high" if status == "status::verhandlung" else "medium",
            })
    
    return hot_leads


def check_duplicates(issues: List[Dict]) -> List[Tuple[Dict, Dict, float]]:
    """Find potential duplicate issues."""
    duplicates = []
    
    # Compare titles
    for i, issue1 in enumerate(issues):
        for issue2 in issues[i+1:]:
            title1 = issue1.get("title", "").lower()
            title2 = issue2.get("title", "").lower()
            
            # Skip if same issue
            if issue1["iid"] == issue2["iid"]:
                continue
            
            # Calculate similarity
            similarity = SequenceMatcher(None, title1, title2).ratio()
            
            if similarity > 0.8:  # 80% similar
                duplicates.append((issue1, issue2, similarity))
    
    return duplicates


def process_follow_ups(follow_ups: List[Dict]) -> int:
    """Process follow-up reminders."""
    processed = 0
    
    for item in follow_ups:
        issue = item["issue"]
        days = item["days_since"]
        
        print(f"  #{issue['iid']}: {issue['title'][:40]}... ({days} Tage)")
        
        # Add label
        if add_label(issue["iid"], "needs-followup"):
            processed += 1
        
        # Add comment
        comment = f"""⏰ **Follow-up Erinnerung**

Keine Aktivität seit **{days} Tagen**.

**Empfohlene Aktionen:**
- [ ] Nachfass-Email senden
- [ ] Telefonisch nachfragen
- [ ] Status aktualisieren

_Automatisch generiert am {datetime.now().strftime('%d.%m.%Y %H:%M')}_"""
        
        add_comment(issue["iid"], comment)
    
    return processed


def process_ghosts(ghosts: List[Dict]) -> int:
    """Process ghost detection."""
    processed = 0
    
    for item in ghosts:
        issue = item["issue"]
        days = item["days_since"]
        
        print(f"  #{issue['iid']}: {issue['title'][:40]}... ({days} Tage)")
        
        # Add ghost label, remove old status
        if add_label(issue["iid"], "status::ghost"):
            processed += 1
        
        # Add comment
        comment = f"""👻 **Als Ghost markiert**

Keine Aktivität seit **{days} Tagen** (>{GHOST_DAYS} Tage Limit).

Diese Bewerbung wird als "Ghost" klassifiziert - wahrscheinlich keine Antwort mehr zu erwarten.

**Optionen:**
- Issue schließen wenn aufgegeben
- Erneut nachfassen als letzter Versuch
- Label entfernen wenn doch Aktivität

_Automatisch generiert am {datetime.now().strftime('%d.%m.%Y %H:%M')}_"""
        
        add_comment(issue["iid"], comment)
    
    return processed


def main():
    print("=" * 60)
    print("CRM Smart Automation")
    print("=" * 60)
    
    if not GITLAB_TOKEN:
        print("❌ ERROR: GITLAB_TOKEN not set")
        sys.exit(1)
    
    if DRY_RUN:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    print(f"\nConfig:")
    print(f"  Follow-up after: {FOLLOW_UP_DAYS} days")
    print(f"  Ghost after: {GHOST_DAYS} days")
    
    # Fetch issues
    print("\n📥 Fetching issues...")
    issues = fetch_all_issues("opened")
    print(f"   Found {len(issues)} open issues")
    
    results = {
        "follow_ups": 0,
        "ghosts": 0,
        "hot_leads": 0,
        "duplicates": 0,
    }
    
    # Check follow-ups
    print(f"\n⏰ Checking follow-ups (>{FOLLOW_UP_DAYS} days)...")
    follow_ups = check_follow_ups(issues)
    print(f"   Found {len(follow_ups)} issues needing follow-up")
    
    if follow_ups:
        results["follow_ups"] = process_follow_ups(follow_ups)
    
    # Check ghosts
    print(f"\n👻 Checking ghosts (>{GHOST_DAYS} days)...")
    ghosts = check_ghosts(issues)
    print(f"   Found {len(ghosts)} potential ghosts")
    
    if ghosts:
        results["ghosts"] = process_ghosts(ghosts)
    
    # Check hot leads
    print("\n🔥 Checking hot leads...")
    hot_leads = check_hot_leads(issues)
    print(f"   Found {len(hot_leads)} active hot leads")
    
    for hl in hot_leads:
        issue = hl["issue"]
        print(f"   🔥 #{issue['iid']}: {issue['title'][:40]}... [{hl['status']}]")
    results["hot_leads"] = len(hot_leads)
    
    # Check duplicates
    print("\n🔍 Checking duplicates...")
    duplicates = check_duplicates(issues)
    print(f"   Found {len(duplicates)} potential duplicates")
    
    for dup in duplicates[:5]:  # Show max 5
        print(f"   ⚠️ #{dup[0]['iid']} ~ #{dup[1]['iid']} ({dup[2]*100:.0f}% similar)")
    results["duplicates"] = len(duplicates)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  ⏰ Follow-ups processed: {results['follow_ups']}")
    print(f"  👻 Ghosts marked: {results['ghosts']}")
    print(f"  🔥 Hot leads active: {results['hot_leads']}")
    print(f"  🔍 Duplicates found: {results['duplicates']}")
    
    # Save results
    os.makedirs("output", exist_ok=True)
    with open("output/crm_automation_results.json", "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "dry_run": DRY_RUN,
            "results": results,
            "follow_ups": [{"iid": f["issue"]["iid"], "days": f["days_since"]} for f in follow_ups],
            "ghosts": [{"iid": g["issue"]["iid"], "days": g["days_since"]} for g in ghosts],
            "hot_leads": [{"iid": h["issue"]["iid"], "status": h["status"]} for h in hot_leads],
        }, f, indent=2)
    
    print("\n✅ Results saved to output/crm_automation_results.json")


if __name__ == "__main__":
    main()
