#!/usr/bin/env python3
"""
CRM Integrity Check — Standalone Weekly Health Monitor

Validates CRM data quality, detects anomalies, and reports metrics.
Designed to run as a scheduled pipeline job (weekly).

Exit codes:
  0 = Healthy
  1 = Critical issues found
  2 = Warnings only
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from collections import Counter, defaultdict
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN", "")
GITLAB_API = "https://gitlab.com/api/v4"
CRM_PROJECT_ID = os.environ.get("CRM_PROJECT_ID", "78171527")
GROUP_ID = os.environ.get("GROUP_ID", "120698013")
QA_REPORT = "output/crm_qa_report.json"


class QAReport:
    def __init__(self):
        self.tests = []
        self.failures = 0
        self.warnings = 0
        self.passed = 0

    def ok(self, name, detail=""):
        self.tests.append({"name": name, "status": "passed", "detail": detail})
        self.passed += 1
        print(f"  ✅ {name}" + (f" ({detail})" if detail else ""))

    def fail(self, name, detail=""):
        self.tests.append({"name": name, "status": "failed", "detail": detail})
        self.failures += 1
        print(f"  ❌ FAIL: {name} — {detail}")

    def warn(self, name, detail=""):
        self.tests.append({"name": name, "status": "warning", "detail": detail})
        self.warnings += 1
        print(f"  ⚠️  WARN: {name} — {detail}")

    def to_json(self):
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {"total": len(self.tests), "passed": self.passed,
                        "failures": self.failures, "warnings": self.warnings},
            "tests": self.tests
        }, indent=2)

    @property
    def exit_code(self):
        """Exit codes: 0=success (incl. warnings), 1=failures. (#43)"""
        if self.failures > 0: return 1
        return 0  # Warnings are informational, not blocking


def api_get(path, params=""):
    """Helper for GitLab API GET requests."""
    url = f"{GITLAB_API}{path}{'&' if '?' in path else '?'}{params}" if params else f"{GITLAB_API}{path}"
    req = urllib.request.Request(url, headers={"PRIVATE-TOKEN": GITLAB_TOKEN})
    return json.loads(urllib.request.urlopen(req).read())


def fetch_all_issues():
    """Fetch all CRM issues (paginated)."""
    issues = []
    page = 1
    while True:
        batch = api_get(f"/projects/{CRM_PROJECT_ID}/issues?per_page=100&page={page}&state=all")
        if not batch:
            break
        issues.extend(batch)
        page += 1
    return issues


def fetch_group_labels():
    """Fetch all group-level labels."""
    labels = []
    page = 1
    while True:
        batch = api_get(f"/groups/{GROUP_ID}/labels?per_page=100&page={page}")
        if not batch:
            break
        labels.extend(batch)
        page += 1
    return labels


# ═══════════════════════════════════════════════════════════════
# CHECKS
# ═══════════════════════════════════════════════════════════════

def check_connectivity(report):
    """Verify API access."""
    print("\n━━━ CONNECTIVITY ━━━")
    if not GITLAB_TOKEN:
        report.fail("api.token", "GITLAB_TOKEN not set")
        return False
    try:
        project = api_get(f"/projects/{CRM_PROJECT_ID}")
        report.ok("api.crm_access", project["path_with_namespace"])
        return True
    except Exception as e:
        report.fail("api.crm_access", str(e))
        return False


def check_status_integrity(report, issues):
    """Every open issue must have exactly one status:: label."""
    print("\n━━━ STATUS INTEGRITY ━━━")
    open_issues = [i for i in issues if i["state"] == "opened"]
    no_status = []
    multi_status = []

    for i in open_issues:
        statuses = [l for l in i["labels"] if l.startswith("status::")]
        if len(statuses) == 0:
            no_status.append(i["iid"])
        elif len(statuses) > 1:
            multi_status.append((i["iid"], statuses))

    if no_status:
        report.fail("status.all_have_one", f"{len(no_status)} without status: {no_status[:5]}")
    else:
        report.ok("status.all_have_one", f"{len(open_issues)} issues checked")

    if multi_status:
        report.fail("status.no_multiples", f"{len(multi_status)} with >1 status")
    else:
        report.ok("status.no_multiples")


def check_label_consistency(report, issues, group_labels):
    """All labels on issues should exist as group labels."""
    print("\n━━━ LABEL CONSISTENCY ━━━")
    valid_labels = {l["name"] for l in group_labels}

    orphan_labels = set()
    for i in issues:
        for l in i["labels"]:
            if l not in valid_labels:
                orphan_labels.add(l)

    if orphan_labels:
        report.warn("labels.all_valid", f"{len(orphan_labels)} unknown: {list(orphan_labels)[:5]}")
    else:
        report.ok("labels.all_valid", f"All labels match group definitions")

    # Check for unused labels
    used_labels = set()
    for i in issues:
        used_labels.update(i["labels"])
    unused = valid_labels - used_labels
    status_unused = [l for l in unused if l.startswith("status::")]
    if status_unused:
        report.ok("labels.status_coverage", f"Unused status labels: {status_unused}")
    else:
        report.ok("labels.status_coverage", "All status labels in use")


def check_duplicates(report, issues):
    """Detect duplicate issue titles."""
    print("\n━━━ DUPLICATE DETECTION ━━━")
    open_issues = [i for i in issues if i["state"] == "opened"]
    title_counts = Counter(i["title"] for i in open_issues)
    dupes = {t: c for t, c in title_counts.items() if c > 1}

    if dupes:
        report.warn("dupes.titles", f"{len(dupes)} duplicate titles: " +
                    ", ".join(f'"{t[:40]}..." ({c}x)' for t, c in list(dupes.items())[:3]))
    else:
        report.ok("dupes.titles", f"{len(title_counts)} unique titles")


def check_ghost_candidates(report, issues):
    """Detect issues stuck in 'versendet' for >14 days without activity."""
    print("\n━━━ GHOST DETECTION ━━━")
    now = datetime.utcnow()
    threshold = now - timedelta(days=14)

    ghosts = []
    for i in issues:
        if i["state"] != "opened":
            continue
        statuses = [l for l in i["labels"] if l.startswith("status::")]
        if "status::versendet" not in statuses:
            continue
        # Check last update
        updated = datetime.fromisoformat(i["updated_at"].replace("Z", "+00:00")).replace(tzinfo=None)
        if updated < threshold:
            days = (now - updated).days
            ghosts.append((i["iid"], i["title"][:40], days))

    if ghosts:
        report.warn("ghost.stale_versendet",
                    f"{len(ghosts)} issues in 'versendet' >14 days without update. "
                    f"Top: #{ghosts[0][0]} ({ghosts[0][2]}d)")
    else:
        report.ok("ghost.stale_versendet", "No stale issues")


def check_funnel_health(report, issues):
    """Analyze pipeline funnel for anomalies."""
    print("\n━━━ FUNNEL HEALTH ━━━")
    open_issues = [i for i in issues if i["state"] == "opened"]
    status_counts = Counter()
    for i in open_issues:
        for l in i["labels"]:
            if l.startswith("status::"):
                status_counts[l] += 1

    total = len(open_issues)
    print(f"  Pipeline ({total} open):")
    for s in ["status::neu", "status::versendet", "status::beim-kunden",
              "status::interview", "status::verhandlung", "status::zusage",
              "status::absage", "status::ghost"]:
        c = status_counts.get(s, 0)
        pct = c / total * 100 if total else 0
        bar = "█" * int(pct / 2)
        print(f"    {s:25s} {c:4d} ({pct:4.1f}%) {bar}")

    # Anomaly: >95% in one stage (excluding versendet which is normal for early pipeline)
    for s, c in status_counts.items():
        if s == "status::versendet":
            continue
        if c / total > 0.5:
            report.warn("funnel.concentration", f"{s} has {c/total*100:.0f}% of all issues")
            return

    # Anomaly: zero in interview/verhandlung/zusage (cold pipeline)
    active = sum(status_counts.get(s, 0)
                 for s in ["status::beim-kunden", "status::interview",
                           "status::verhandlung", "status::zusage"])
    if active == 0:
        report.warn("funnel.no_active", "No issues past 'versendet' — pipeline is cold")
    else:
        report.ok("funnel.active", f"{active} issues in active stages")

    report.ok("funnel.distribution")


def check_rate_coverage(report, issues):
    """Verify rate labels are present."""
    print("\n━━━ RATE COVERAGE ━━━")
    open_issues = [i for i in issues if i["state"] == "opened"]
    has_rate = sum(1 for i in open_issues if any(l.startswith("rate::") for l in i["labels"]))
    pct = has_rate / len(open_issues) * 100 if open_issues else 0

    if pct >= 90:   report.ok("rate.coverage", f"{pct:.0f}%")
    elif pct >= 70: report.warn("rate.coverage", f"Only {pct:.0f}%")
    else:           report.fail("rate.coverage", f"Low: {pct:.0f}%")

    # Rate distribution
    rate_counts = Counter()
    for i in open_issues:
        for l in i["labels"]:
            if l.startswith("rate::"):
                rate_counts[l] += 1
    if rate_counts:
        dist = ", ".join(f"{k.split('::')[1]}={v}" for k, v in sorted(rate_counts.items()))
        report.ok("rate.distribution", dist)


def check_hot_leads(report, issues):
    """Report on hot lead status."""
    print("\n━━━ HOT LEADS ━━━")
    hot = [i for i in issues if "hot-lead" in i["labels"] and i["state"] == "opened"]
    report.ok("hotleads.count", f"{len(hot)} active hot leads")

    # Hot leads with absage (should be cleaned up)
    hot_absage = [i for i in issues if "hot-lead" in i["labels"]
                  and "status::absage" in i["labels"] and i["state"] == "opened"]
    if hot_absage:
        report.warn("hotleads.stale",
                    f"{len(hot_absage)} hot leads with Absage — remove hot-lead label?")
    else:
        report.ok("hotleads.no_stale")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("  CRM INTEGRITY CHECK")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)

    report = QAReport()

    if not check_connectivity(report):
        print("\n❌ Cannot connect to GitLab API — aborting")
        sys.exit(1)

    issues = fetch_all_issues()
    labels = fetch_group_labels()

    print(f"\n📊 Loaded: {len(issues)} issues, {len(labels)} group labels")

    check_status_integrity(report, issues)
    check_label_consistency(report, issues, labels)
    check_duplicates(report, issues)
    check_ghost_candidates(report, issues)
    check_funnel_health(report, issues)
    check_rate_coverage(report, issues)
    check_hot_leads(report, issues)

    print(f"\n{'='*70}")
    print(f"  RESULTS: {report.passed}✅  {report.warnings}⚠️  {report.failures}❌")
    print(f"  EXIT: {report.exit_code}")
    print(f"{'='*70}")

    os.makedirs("output", exist_ok=True)
    with open(QA_REPORT, "w") as f:
        f.write(report.to_json())
    print(f"\n📄 {QA_REPORT}")

    sys.exit(report.exit_code)

if __name__ == "__main__":
    main()
