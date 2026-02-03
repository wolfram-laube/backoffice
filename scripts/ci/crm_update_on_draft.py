#!/usr/bin/env python3
"""
CRM Update on Draft Creation

Updates GitLab Issues in CRM repo when Gmail drafts are created.
- Finds existing issue by title/agency match
- Adds timeline comment with draft details
- Creates new issue if no match found

Required env:
  - GITLAB_TOKEN
  - CRM_PROJECT_ID (default: 78171527)

Input: output/matches.json or DRAFTS_JSON_B64
"""

import json
import os
import sys
import base64
import urllib.request
import urllib.parse
from datetime import datetime
from typing import Optional, Dict, List, Any

# Config
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN") or os.environ.get("GITLAB_API_TOKEN")
CRM_PROJECT_ID = os.environ.get("CRM_PROJECT_ID", "78171527")
GITLAB_API = "https://gitlab.com/api/v4"
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"


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
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"  ⚠️ API Error {e.code}: {error_body[:200]}")
        return None


def search_issue_by_title(search_term: str) -> Optional[Dict]:
    """Search for existing CRM issue by title."""
    encoded = urllib.parse.quote(search_term)
    endpoint = f"/projects/{CRM_PROJECT_ID}/issues?search={encoded}&state=opened&per_page=10"
    issues = api_request("GET", endpoint)
    
    if not issues:
        return None
    
    # Find best match
    search_lower = search_term.lower()
    for issue in issues:
        title_lower = issue.get("title", "").lower()
        if search_lower in title_lower or title_lower in search_lower:
            return issue
    
    return None


def search_issue_by_agency_position(agency: str, position: str) -> Optional[Dict]:
    """Search for existing CRM issue by agency and position."""
    # Try agency first
    if agency:
        issue = search_issue_by_title(agency)
        if issue:
            return issue
    
    # Try position keywords
    if position:
        keywords = position.split()[:3]  # First 3 words
        for kw in keywords:
            if len(kw) > 4:  # Skip short words
                issue = search_issue_by_title(kw)
                if issue:
                    return issue
    
    return None


def add_comment_to_issue(issue_iid: int, comment: str) -> bool:
    """Add timeline comment to CRM issue."""
    if DRY_RUN:
        print(f"  [DRY RUN] Would add comment to issue #{issue_iid}")
        return True
    
    endpoint = f"/projects/{CRM_PROJECT_ID}/issues/{issue_iid}/notes"
    result = api_request("POST", endpoint, {"body": comment})
    return result is not None


def create_crm_issue(title: str, description: str, labels: List[str]) -> Optional[int]:
    """Create new CRM issue."""
    if DRY_RUN:
        print(f"  [DRY RUN] Would create issue: {title}")
        return 9999
    
    endpoint = f"/projects/{CRM_PROJECT_ID}/issues"
    data = {
        "title": title,
        "description": description,
        "labels": ",".join(labels),
    }
    result = api_request("POST", endpoint, data)
    if result:
        return result.get("iid")
    return None


def update_issue_labels(issue_iid: int, add_labels: List[str]) -> bool:
    """Add labels to existing issue."""
    if DRY_RUN:
        print(f"  [DRY RUN] Would add labels {add_labels} to #{issue_iid}")
        return True
    
    endpoint = f"/projects/{CRM_PROJECT_ID}/issues/{issue_iid}"
    data = {"add_labels": ",".join(add_labels)}
    result = api_request("PUT", endpoint, data)
    return result is not None


def format_draft_comment(draft: Dict) -> str:
    """Format timeline comment for draft creation."""
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    to_addr = draft.get("to", "?")
    subject = draft.get("subject", "?")
    
    comment = f"""📤 **{now} — Gmail-Draft erstellt**

**An:** {to_addr}
**Betreff:** {subject}

_Draft wurde automatisch via CI/CD Pipeline erstellt._
"""
    return comment


def format_new_issue_description(draft: Dict) -> str:
    """Format description for new CRM issue."""
    to_addr = draft.get("to", "?")
    subject = draft.get("subject", "?")
    agency = draft.get("agency", "Unbekannt")
    position = draft.get("position", subject)
    
    description = f"""### Meta
- **Agentur:** {agency}
- **Kontakt:** {to_addr}
- **Email:** {to_addr}
- **Position:** {position}
- **Rate:** TBD
- **Remote:** TBD

### Anforderungen
_Aus Crawl-Daten übernehmen_

### Match-Analyse
_TBD_

---
_Issue automatisch erstellt via CI/CD Pipeline_
"""
    return description


def process_draft(draft: Dict, index: int) -> Dict:
    """Process single draft and update CRM."""
    to_addr = draft.get("to", "")
    subject = draft.get("subject", "")
    agency = draft.get("agency", "")
    position = draft.get("position", subject)
    
    print(f"\n[{index+1}] Processing: {subject[:60]}...")
    print(f"    To: {to_addr}")
    
    result = {
        "subject": subject,
        "to": to_addr,
        "action": None,
        "issue_iid": None,
    }
    
    # Search for existing issue
    existing = search_issue_by_agency_position(agency, position)
    
    if existing:
        issue_iid = existing["iid"]
        print(f"    ✅ Found existing issue #{issue_iid}: {existing['title'][:50]}")
        
        # Add comment
        comment = format_draft_comment(draft)
        if add_comment_to_issue(issue_iid, comment):
            print(f"    ✅ Added timeline comment")
            result["action"] = "commented"
            result["issue_iid"] = issue_iid
        
        # Update status label if needed
        labels = [l["name"] for l in existing.get("labels", [])]
        if "status::neu" in labels:
            update_issue_labels(issue_iid, ["status::versendet"])
            print(f"    ✅ Updated status: neu → versendet")
    
    else:
        print(f"    ℹ️ No existing issue found, creating new...")
        
        # Create new issue
        title = f"{position[:80]} ({agency})" if agency else position[:100]
        description = format_new_issue_description(draft)
        labels = ["status::versendet", "source::pipeline"]
        
        new_iid = create_crm_issue(title, description, labels)
        if new_iid:
            print(f"    ✅ Created new issue #{new_iid}")
            result["action"] = "created"
            result["issue_iid"] = new_iid
            
            # Add initial comment
            comment = format_draft_comment(draft)
            add_comment_to_issue(new_iid, comment)
    
    return result


def load_drafts() -> List[Dict]:
    """Load drafts from matches.json or DRAFTS_JSON_B64."""
    drafts = []
    
    # Try matches.json first (from applications pipeline)
    if os.path.exists("output/matches.json"):
        print("Loading from output/matches.json...")
        with open("output/matches.json", "r") as f:
            matches = json.load(f)
            for m in matches:
                drafts.append({
                    "to": m.get("contact_email", m.get("email", "")),
                    "subject": m.get("title", m.get("position", "")),
                    "agency": m.get("agency", ""),
                    "position": m.get("position", m.get("title", "")),
                })
    
    # Try DRAFTS_JSON_B64 (from gmail-drafts pipeline)
    elif os.environ.get("DRAFTS_JSON_B64"):
        print("Loading from DRAFTS_JSON_B64...")
        decoded = base64.b64decode(os.environ["DRAFTS_JSON_B64"]).decode("utf-8")
        raw_drafts = json.loads(decoded)
        for d in raw_drafts:
            drafts.append({
                "to": d.get("to", ""),
                "subject": d.get("subject", ""),
                "agency": d.get("agency", ""),
                "position": d.get("subject", ""),
            })
    
    # Try draft_results.json (output from gmail:create-drafts)
    elif os.path.exists("output/draft_results.json"):
        print("Loading from output/draft_results.json...")
        with open("output/draft_results.json", "r") as f:
            drafts = json.load(f)
    
    return drafts


def main():
    print("=" * 60)
    print("CRM Update on Draft Creation")
    print("=" * 60)
    
    if not GITLAB_TOKEN:
        print("❌ ERROR: GITLAB_TOKEN not set")
        sys.exit(1)
    
    if DRY_RUN:
        print("🔍 DRY RUN MODE - No changes will be made")
    
    print(f"CRM Project ID: {CRM_PROJECT_ID}")
    
    # Load drafts
    drafts = load_drafts()
    
    if not drafts:
        print("\n⚠️ No drafts found to process")
        print("Expected: output/matches.json, output/draft_results.json, or DRAFTS_JSON_B64")
        sys.exit(0)
    
    print(f"\nFound {len(drafts)} draft(s) to process")
    
    # Process each draft
    results = []
    for i, draft in enumerate(drafts):
        result = process_draft(draft, i)
        results.append(result)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    created = sum(1 for r in results if r["action"] == "created")
    commented = sum(1 for r in results if r["action"] == "commented")
    failed = sum(1 for r in results if r["action"] is None)
    
    print(f"  ✅ Created:   {created}")
    print(f"  💬 Commented: {commented}")
    print(f"  ❌ Failed:    {failed}")
    
    # Save results
    os.makedirs("output", exist_ok=True)
    with open("output/crm_update_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("\nResults saved to output/crm_update_results.json")
    
    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()