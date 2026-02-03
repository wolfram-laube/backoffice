#!/usr/bin/env python3
"""
CRM Reporting - Weekly & Monthly Analytics

Generates performance reports from GitLab Issues CRM data.
- Funnel metrics & conversion rates
- Response time analysis
- Agency performance ranking
- Rate analytics by tech/industry
- Trend comparison (week-over-week, month-over-month)

Required env:
  - GITLAB_TOKEN
  - CRM_PROJECT_ID (default: 78171527)

Optional env:
  - REPORT_TYPE: "weekly" or "monthly" (default: weekly)
  - SEND_EMAIL: "true" to send via Gmail
"""

import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any, Optional

# Config
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN") or os.environ.get("GITLAB_API_TOKEN")
CRM_PROJECT_ID = os.environ.get("CRM_PROJECT_ID", "78171527")
GITLAB_API = "https://gitlab.com/api/v4"
REPORT_TYPE = os.environ.get("REPORT_TYPE", "weekly")


def api_request(endpoint: str) -> Any:
    """Make GitLab API request."""
    url = f"{GITLAB_API}{endpoint}"
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"API Error {e.code}: {e.read().decode()[:200]}")
        return None


def fetch_all_issues() -> List[Dict]:
    """Fetch all CRM issues with pagination."""
    all_issues = []
    page = 1
    
    while True:
        endpoint = f"/projects/{CRM_PROJECT_ID}/issues?state=all&per_page=100&page={page}"
        issues = api_request(endpoint)
        
        if not issues:
            break
        
        # Filter out epics and infrastructure
        for issue in issues:
            labels = [l.get("name", l) if isinstance(l, dict) else l for l in issue.get("labels", [])]
            if "epic" not in labels and "infrastructure" not in labels:
                issue["_labels"] = labels
                all_issues.append(issue)
        
        if len(issues) < 100:
            break
        page += 1
    
    return all_issues


def get_status(issue: Dict) -> str:
    """Extract status from issue labels."""
    status_map = {
        "status::neu": "Neu",
        "status::versendet": "Versendet",
        "status::beim-kunden": "Beim Kunden",
        "status::interview": "Interview",
        "status::verhandlung": "Verhandlung",
        "status::zusage": "Zusage",
        "status::absage": "Absage",
        "status::ghost": "Ghost",
    }
    
    for label in issue.get("_labels", []):
        if label in status_map:
            return status_map[label]
    return "Unbekannt"


def get_rate_range(issue: Dict) -> Optional[str]:
    """Extract rate range from labels."""
    for label in issue.get("_labels", []):
        if label.startswith("rate::"):
            return label.replace("rate::", "")
    return None


def parse_date(date_str: str) -> datetime:
    """Parse ISO date string."""
    return datetime.fromisoformat(date_str.replace("Z", "+00:00"))


def calculate_funnel(issues: List[Dict]) -> Dict[str, int]:
    """Calculate funnel metrics."""
    funnel = defaultdict(int)
    
    for issue in issues:
        status = get_status(issue)
        funnel[status] += 1
    
    return dict(funnel)


def calculate_conversion_rates(funnel: Dict[str, int]) -> Dict[str, float]:
    """Calculate conversion rates between stages."""
    total = sum(funnel.values())
    if total == 0:
        return {}
    
    stages = ["Versendet", "Beim Kunden", "Interview", "Verhandlung", "Zusage"]
    rates = {}
    
    # Overall conversion
    zusagen = funnel.get("Zusage", 0)
    rates["overall"] = (zusagen / total * 100) if total > 0 else 0
    
    # Stage-to-stage
    prev_count = funnel.get("Versendet", 0) + funnel.get("Neu", 0)
    for stage in stages[1:]:
        current = funnel.get(stage, 0)
        if prev_count > 0:
            rates[f"to_{stage.lower().replace(' ', '_')}"] = current / prev_count * 100
        prev_count = current if current > 0 else prev_count
    
    return rates


def analyze_by_period(issues: List[Dict], days: int) -> Dict[str, Any]:
    """Analyze issues created/updated in last N days."""
    cutoff = datetime.now().astimezone() - timedelta(days=days)
    
    new_issues = []
    updated_issues = []
    status_changes = defaultdict(int)
    
    for issue in issues:
        created = parse_date(issue["created_at"])
        updated = parse_date(issue["updated_at"])
        
        if created > cutoff:
            new_issues.append(issue)
        
        if updated > cutoff and created <= cutoff:
            updated_issues.append(issue)
            status = get_status(issue)
            status_changes[status] += 1
    
    return {
        "new_count": len(new_issues),
        "updated_count": len(updated_issues),
        "status_changes": dict(status_changes),
        "new_issues": new_issues,
    }


def analyze_rates(issues: List[Dict]) -> Dict[str, Any]:
    """Analyze rate distribution."""
    rate_dist = defaultdict(int)
    rates_by_tech = defaultdict(list)
    
    for issue in issues:
        rate = get_rate_range(issue)
        if rate:
            rate_dist[rate] += 1
            
            # Extract tech labels
            for label in issue.get("_labels", []):
                if label.startswith("tech::"):
                    tech = label.replace("tech::", "")
                    # Map rate to numeric for averaging
                    rate_val = {"85-95": 90, "95-105": 100, "105+": 110}.get(rate, 0)
                    if rate_val:
                        rates_by_tech[tech].append(rate_val)
    
    # Calculate averages
    avg_by_tech = {}
    for tech, rates in rates_by_tech.items():
        if rates:
            avg_by_tech[tech] = sum(rates) / len(rates)
    
    return {
        "distribution": dict(rate_dist),
        "avg_by_tech": avg_by_tech,
    }


def analyze_agencies(issues: List[Dict]) -> List[Dict]:
    """Analyze agency performance (from issue titles)."""
    agency_stats = defaultdict(lambda: {"total": 0, "success": 0, "interview": 0})
    
    for issue in issues:
        title = issue.get("title", "")
        status = get_status(issue)
        
        # Extract agency from title pattern: "[Agency Name] ..."
        if title.startswith("[") and "]" in title:
            agency = title[1:title.index("]")]
        else:
            agency = "Direct/Unknown"
        
        agency_stats[agency]["total"] += 1
        if status == "Zusage":
            agency_stats[agency]["success"] += 1
        if status in ["Interview", "Verhandlung", "Zusage"]:
            agency_stats[agency]["interview"] += 1
    
    # Convert to sorted list
    result = []
    for agency, stats in agency_stats.items():
        success_rate = (stats["success"] / stats["total"] * 100) if stats["total"] > 0 else 0
        interview_rate = (stats["interview"] / stats["total"] * 100) if stats["total"] > 0 else 0
        result.append({
            "agency": agency,
            "total": stats["total"],
            "interviews": stats["interview"],
            "success": stats["success"],
            "interview_rate": round(interview_rate, 1),
            "success_rate": round(success_rate, 1),
        })
    
    # Sort by total descending
    result.sort(key=lambda x: x["total"], reverse=True)
    return result[:15]  # Top 15


def count_hot_leads(issues: List[Dict]) -> int:
    """Count active hot leads."""
    count = 0
    for issue in issues:
        if issue.get("state") == "opened" and "hot-lead" in issue.get("_labels", []):
            count += 1
    return count


def generate_report(issues: List[Dict], report_type: str) -> str:
    """Generate markdown report."""
    now = datetime.now()
    days = 7 if report_type == "weekly" else 30
    period_name = "Woche" if report_type == "weekly" else "Monat"
    
    # Calculate metrics
    funnel = calculate_funnel(issues)
    conversions = calculate_conversion_rates(funnel)
    period_stats = analyze_by_period(issues, days)
    rate_stats = analyze_rates(issues)
    agency_stats = analyze_agencies(issues)
    hot_leads = count_hot_leads(issues)
    
    total = len(issues)
    active = sum(1 for i in issues if i.get("state") == "opened")
    
    # Build report
    report = f"""# CRM Report - {period_name} {now.strftime('%d.%m.%Y')}

## 📊 Übersicht

| Metrik | Wert |
|--------|------|
| **Gesamt Bewerbungen** | {total} |
| **Aktiv (offen)** | {active} |
| **🔥 Hot Leads** | {hot_leads} |
| **Neue diese {period_name}** | {period_stats['new_count']} |
| **Updates diese {period_name}** | {period_stats['updated_count']} |

## 📈 Funnel

| Stage | Anzahl | % |
|-------|--------|---|
"""
    
    for stage in ["Neu", "Versendet", "Beim Kunden", "Interview", "Verhandlung", "Zusage", "Absage", "Ghost"]:
        count = funnel.get(stage, 0)
        pct = (count / total * 100) if total > 0 else 0
        bar = "█" * int(pct / 5)
        report += f"| {stage} | {count} | {pct:.1f}% {bar} |\n"
    
    report += f"""
## 🎯 Conversion Rates

| Metrik | Rate |
|--------|------|
| **Gesamtconversion** (→ Zusage) | {conversions.get('overall', 0):.1f}% |
| Versendet → Beim Kunden | {conversions.get('to_beim_kunden', 0):.1f}% |
| Beim Kunden → Interview | {conversions.get('to_interview', 0):.1f}% |
| Interview → Verhandlung | {conversions.get('to_verhandlung', 0):.1f}% |
| Verhandlung → Zusage | {conversions.get('to_zusage', 0):.1f}% |

## 💰 Raten-Analyse

| Rate | Anzahl |
|------|--------|
"""
    
    for rate, count in sorted(rate_stats["distribution"].items()):
        report += f"| {rate} €/h | {count} |\n"
    
    if rate_stats["avg_by_tech"]:
        report += "\n**Durchschnittsrate nach Technologie:**\n"
        for tech, avg in sorted(rate_stats["avg_by_tech"].items(), key=lambda x: -x[1])[:5]:
            report += f"- {tech}: {avg:.0f} €/h\n"
    
    report += f"""
## 🏢 Top Agenturen

| Agentur | Gesamt | Interviews | Erfolge | Interview-Rate |
|---------|--------|------------|---------|----------------|
"""
    
    for a in agency_stats[:10]:
        report += f"| {a['agency'][:25]} | {a['total']} | {a['interviews']} | {a['success']} | {a['interview_rate']}% |\n"
    
    # Recent activity
    if period_stats["new_issues"]:
        report += f"\n## 🆕 Neue Bewerbungen diese {period_name}\n\n"
        for issue in period_stats["new_issues"][:10]:
            status = get_status(issue)
            report += f"- #{issue['iid']}: {issue['title'][:50]}... ({status})\n"
        if len(period_stats["new_issues"]) > 10:
            report += f"- ... und {len(period_stats['new_issues']) - 10} weitere\n"
    
    report += f"""
---
*Generiert am {now.strftime('%d.%m.%Y %H:%M')} UTC*
"""
    
    return report


def generate_json_report(issues: List[Dict], report_type: str) -> Dict:
    """Generate JSON report for programmatic use."""
    days = 7 if report_type == "weekly" else 30
    
    funnel = calculate_funnel(issues)
    conversions = calculate_conversion_rates(funnel)
    period_stats = analyze_by_period(issues, days)
    rate_stats = analyze_rates(issues)
    agency_stats = analyze_agencies(issues)
    
    return {
        "generated_at": datetime.now().isoformat(),
        "report_type": report_type,
        "total_issues": len(issues),
        "active_issues": sum(1 for i in issues if i.get("state") == "opened"),
        "hot_leads": count_hot_leads(issues),
        "funnel": funnel,
        "conversions": conversions,
        "period_stats": {
            "days": days,
            "new_count": period_stats["new_count"],
            "updated_count": period_stats["updated_count"],
            "status_changes": period_stats["status_changes"],
        },
        "rates": rate_stats,
        "top_agencies": agency_stats[:10],
    }


def main():
    print("=" * 60)
    print(f"CRM Reporting - {REPORT_TYPE.upper()}")
    print("=" * 60)
    
    if not GITLAB_TOKEN:
        print("❌ ERROR: GITLAB_TOKEN not set")
        sys.exit(1)
    
    # Fetch data
    print("\n📥 Fetching issues...")
    issues = fetch_all_issues()
    print(f"   Found {len(issues)} issues")
    
    # Generate reports
    print("\n📝 Generating reports...")
    
    md_report = generate_report(issues, REPORT_TYPE)
    json_report = generate_json_report(issues, REPORT_TYPE)
    
    # Save reports
    os.makedirs("output", exist_ok=True)
    
    md_path = f"output/crm_report_{REPORT_TYPE}.md"
    with open(md_path, "w") as f:
        f.write(md_report)
    print(f"   ✅ Markdown: {md_path}")
    
    json_path = f"output/crm_report_{REPORT_TYPE}.json"
    with open(json_path, "w") as f:
        json.dump(json_report, f, indent=2)
    print(f"   ✅ JSON: {json_path}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Total:      {json_report['total_issues']}")
    print(f"  Active:     {json_report['active_issues']}")
    print(f"  Hot Leads:  {json_report['hot_leads']}")
    print(f"  New ({REPORT_TYPE}): {json_report['period_stats']['new_count']}")
    print(f"  Conversion: {json_report['conversions'].get('overall', 0):.1f}%")
    
    # Print markdown report
    print("\n" + md_report)


if __name__ == "__main__":
    main()
