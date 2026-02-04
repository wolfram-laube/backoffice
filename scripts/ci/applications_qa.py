#!/usr/bin/env python3
"""
Applications Pipeline QA — Stage 3 Validation

Validates crawl + match outputs before drafts are created.
Optionally checks CRM for duplicates (--crm-dedup flag).

Exit codes:
  0 = All checks passed
  1 = Critical failure (blocks pipeline)
  2 = Warnings only (pipeline continues)
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

CRAWL_OUTPUT = "output/projects.json"
MATCH_OUTPUT = "output/matches.json"
QA_REPORT_OUTPUT = "output/qa_report.json"

GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN", "")
GITLAB_API = "https://gitlab.com/api/v4"
CRM_PROJECT_ID = os.environ.get("CRM_PROJECT_ID", "78171527")

CRM_DEDUP = "--crm-dedup" in sys.argv


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

    def to_junit(self):
        cases = []
        for t in self.tests:
            name = t["name"].replace('"', '&quot;')
            detail = t["detail"].replace('"', '&quot;').replace('<', '&lt;')
            if t["status"] == "passed":
                cases.append(f'    <testcase name="{name}" classname="applications.qa" />')
            elif t["status"] == "failed":
                cases.append(f'    <testcase name="{name}" classname="applications.qa">')
                cases.append(f'      <failure message="{detail}" />')
                cases.append(f'    </testcase>')
            else:
                cases.append(f'    <testcase name="{name}" classname="applications.qa">')
                cases.append(f'      <system-out>{detail}</system-out>')
                cases.append(f'    </testcase>')
        return "\n".join([
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<testsuites tests="{len(self.tests)}" failures="{self.failures}">',
            f'  <testsuite name="applications-qa" tests="{len(self.tests)}" failures="{self.failures}">',
            *cases,
            '  </testsuite>',
            '</testsuites>'
        ])

    def to_json(self):
        return json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {"total": len(self.tests), "passed": self.passed,
                        "failures": self.failures, "warnings": self.warnings},
            "tests": self.tests
        }, indent=2)

    @property
    def exit_code(self):
        if self.failures > 0: return 1
        if self.warnings > 0: return 2
        return 0


def validate_crawl(report):
    print("\n━━━ CRAWL OUTPUT VALIDATION ━━━")
    if not os.path.exists(CRAWL_OUTPUT):
        report.fail("crawl.file_exists", f"{CRAWL_OUTPUT} not found")
        return None
    try:
        with open(CRAWL_OUTPUT) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        report.fail("crawl.valid_json", str(e))
        return None

    report.ok("crawl.file_exists")
    report.ok("crawl.valid_json")

    if not isinstance(data, list):
        report.fail("crawl.is_array", f"Got {type(data).__name__}")
        return None
    if len(data) == 0:
        report.fail("crawl.non_empty", "No projects")
        return data

    report.ok("crawl.non_empty", f"{len(data)} projects")

    # Required fields
    missing = sum(1 for p in data for f in ["title", "url"] if not p.get(f))
    if missing == 0:
        report.ok("crawl.required_fields")
    else:
        report.fail("crawl.required_fields", f"{missing} missing")

    # Description coverage (>70% ok, >40% warn, else fail)
    with_desc = sum(1 for p in data if p.get("description"))
    pct = with_desc / len(data) * 100
    if pct >= 70:   report.ok("crawl.description_coverage", f"{pct:.0f}%")
    elif pct >= 40: report.warn("crawl.description_coverage", f"{pct:.0f}%")
    else:           report.fail("crawl.description_coverage", f"{pct:.0f}%")

    # Duplicate URLs
    urls = [p.get("url", "") for p in data]
    dupes = len(urls) - len(set(urls))
    if dupes == 0:  report.ok("crawl.no_duplicate_urls")
    else:           report.warn("crawl.no_duplicate_urls", f"{dupes} dupes")

    return data


def validate_match(report, crawl_data):
    print("\n━━━ MATCH OUTPUT VALIDATION ━━━")
    if not os.path.exists(MATCH_OUTPUT):
        report.fail("match.file_exists", f"{MATCH_OUTPUT} not found")
        return None
    try:
        with open(MATCH_OUTPUT) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        report.fail("match.valid_json", str(e))
        return None

    report.ok("match.file_exists")
    report.ok("match.valid_json")

    if not isinstance(data, dict):
        report.fail("match.is_dict", f"Got {type(data).__name__}")
        return None
    report.ok("match.is_dict", f"Profiles: {list(data.keys())}")

    total = 0
    for profile, matches in data.items():
        if not isinstance(matches, list):
            report.fail(f"match.{profile}.is_array")
            continue
        if len(matches) == 0:
            report.warn(f"match.{profile}.non_empty", "0 matches")
        else:
            report.ok(f"match.{profile}.count", f"{len(matches)}")
            total += len(matches)

        # Score range check
        for m in matches:
            score = m.get("score", m.get("match_score", 0))
            if isinstance(score, (int, float)) and (score < 0 or score > 100):
                report.warn(f"match.{profile}.score_range", f"Out of bounds: {score}")
                break

    if total > 0: report.ok("match.total", f"{total}")
    else:         report.fail("match.total", "Zero matches")

    return data


def check_data_quality(report, crawl_data):
    print("\n━━━ DATA QUALITY ━━━")
    if not crawl_data: return

    empty = [p for p in crawl_data if not p.get("title", "").strip()]
    if empty: report.fail("quality.no_empty_titles", f"{len(empty)}")
    else:     report.ok("quality.no_empty_titles")

    bad_urls = [p for p in crawl_data if p.get("url") and not p["url"].startswith("http")]
    if bad_urls: report.warn("quality.url_format", f"{len(bad_urls)} non-HTTP")
    else:        report.ok("quality.url_format")

    descs = [len(p.get("description", "")) for p in crawl_data if p.get("description")]
    if descs:
        avg = sum(descs) / len(descs)
        if avg < 50: report.warn("quality.desc_length", f"Avg {avg:.0f} chars")
        else:        report.ok("quality.desc_length", f"Avg {avg:.0f} chars")


def check_crm_duplicates(report, match_data):
    print("\n━━━ CRM DUPLICATE CHECK ━━━")
    if not GITLAB_TOKEN:
        report.warn("crm.token", "No GITLAB_TOKEN — skipping")
        return

    existing = set()
    page = 1
    while True:
        try:
            req = urllib.request.Request(
                f"{GITLAB_API}/projects/{CRM_PROJECT_ID}/issues?state=opened&per_page=100&page={page}",
                headers={"PRIVATE-TOKEN": GITLAB_TOKEN})
            issues = json.loads(urllib.request.urlopen(req).read())
            if not issues: break
            for i in issues:
                title = i["title"]
                m = re.match(r'\[.*?\]\s*(.*)', title)
                if m: existing.add(m.group(1).strip().lower())
                existing.add(title.strip().lower())
            page += 1
        except urllib.error.HTTPError as e:
            report.warn("crm.api", f"HTTP {e.code}")
            return

    report.ok("crm.fetched", f"{len(existing)} titles")

    if not match_data: return
    total_dupes = 0
    for profile, matches in match_data.items():
        dupes = [m for m in matches if m.get("title", "").strip().lower() in existing]
        if dupes:
            total_dupes += len(dupes)
            report.warn(f"crm.{profile}.dupes", f"{len(dupes)} already in CRM")
        else:
            report.ok(f"crm.{profile}.no_dupes")

    if total_dupes == 0: report.ok("crm.no_dupes_total")
    else: report.warn("crm.dupes_total", f"{total_dupes} (will skip in drafts)")


def main():
    print("=" * 70)
    print("  APPLICATIONS PIPELINE — QA VALIDATION")
    print(f"  {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 70)

    report = QAReport()
    crawl = validate_crawl(report)
    match = validate_match(report, crawl)
    check_data_quality(report, crawl)
    if CRM_DEDUP:
        check_crm_duplicates(report, match)

    print(f"\n{'='*70}")
    print(f"  RESULTS: {report.passed}✅  {report.warnings}⚠️  {report.failures}❌")
    print(f"  EXIT: {report.exit_code}")
    print(f"{'='*70}")

    os.makedirs("output", exist_ok=True)
    with open(QA_REPORT_OUTPUT, "w") as f:
        f.write(report.to_junit())
    print(f"\n📄 {QA_REPORT_OUTPUT}")

    sys.exit(report.exit_code)

if __name__ == "__main__":
    main()
