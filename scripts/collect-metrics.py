#!/usr/bin/env python3
"""CI Metrics Collector — Post-test ingestion script.

Finds JUnit XML report files from CI artifacts and inserts
results directly into BigQuery. Runs as a CI job after test stages.

Usage (CI):
    python scripts/collect-metrics.py

Usage (local test):
    python scripts/collect-metrics.py --xml report.xml --pipeline-id 12345 --job-name test:unit

Environment variables (from GitLab CI):
    CI_PIPELINE_ID, CI_PROJECT_ID, CI_JOB_NAME,
    CI_COMMIT_REF_NAME, CI_COMMIT_SHA, CI_PROJECT_DIR

Ref: Issue #40, ADR INF-001
"""

import argparse
import glob
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone


# ── Config ──────────────────────────────────────────────────────
GCP_PROJECT = os.environ.get("CI_METRICS_GCP_PROJECT", "myk8sproject-207017")
BQ_DATASET = os.environ.get("CI_METRICS_BQ_DATASET", "ci_metrics")

# Known JUnit XML locations from our CI jobs
JUNIT_XML_PATHS = [
    "report.xml",                          # test:unit, test:coverage
    "services/nsai/report.xml",            # test:nsai:unit, test:nsai:notebooks
    "services/ci_metrics/report.xml",      # ci-metrics:test
    "**/report.xml",                       # catch-all glob
]


# ── JUnit XML Parser (standalone, no pydantic dependency) ───────
def parse_junit_xml(xml_path: str) -> dict:
    """Parse a JUnit XML file into structured data.

    Returns dict with keys: suite_name, tests, passed, failed,
    skipped, errors, duration_s, test_cases.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()

    if root.tag == "testsuites":
        suite_elements = root.findall("testsuite")
    elif root.tag == "testsuite":
        suite_elements = [root]
    else:
        print(f"  ⚠️  Unknown root tag '{root.tag}' in {xml_path}")
        return None

    suites = []
    for suite_el in suite_elements:
        test_cases = []

        for tc_el in suite_el.findall("testcase"):
            if tc_el.find("failure") is not None:
                status = "failed"
                msg = tc_el.find("failure").get("message", "")
            elif tc_el.find("error") is not None:
                status = "error"
                msg = tc_el.find("error").get("message", "")
            elif tc_el.find("skipped") is not None:
                status = "skipped"
                msg = tc_el.find("skipped").get("message", "")
            else:
                status = "passed"
                msg = None

            test_cases.append({
                "test_name": tc_el.get("name", "unknown"),
                "classname": tc_el.get("classname", ""),
                "status": status,
                "duration_s": float(tc_el.get("time", 0)),
                "message": (msg[:1000] if msg else None),  # truncate long messages
            })

        tests = int(suite_el.get("tests", len(test_cases)))
        failures = int(suite_el.get("failures", 0))
        errors = int(suite_el.get("errors", 0))
        skipped = int(suite_el.get("skipped", 0))
        passed = tests - failures - errors - skipped

        suites.append({
            "suite_name": suite_el.get("name", os.path.basename(xml_path)),
            "tests": tests,
            "passed": passed,
            "failed": failures,
            "skipped": skipped,
            "errors": errors,
            "duration_s": float(suite_el.get("time", 0)),
            "test_cases": test_cases,
        })

    return suites


# ── BigQuery Insert ─────────────────────────────────────────────
def insert_to_bigquery(suites: list[dict], pipeline_meta: dict) -> int:
    """Insert parsed test results into BigQuery.

    Returns total rows inserted.
    """
    try:
        from google.cloud import bigquery
    except ImportError:
        print("  ❌ google-cloud-bigquery not installed")
        print("     pip install google-cloud-bigquery")
        return 0

    # Auth: in CI, use GCP_SERVICE_ACCOUNT_KEY; locally, use ADC
    sa_key_b64 = os.environ.get("GCP_SERVICE_ACCOUNT_KEY")
    if sa_key_b64:
        import base64
        import tempfile
        from google.oauth2 import service_account

        key_json = base64.b64decode(sa_key_b64).decode()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(key_json)
            key_path = f.name

        credentials = service_account.Credentials.from_service_account_file(
            key_path, scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        client = bigquery.Client(project=GCP_PROJECT, credentials=credentials)
        os.unlink(key_path)
    else:
        # Fall back to Application Default Credentials
        client = bigquery.Client(project=GCP_PROJECT)

    now = datetime.now(timezone.utc).isoformat()
    dataset_ref = f"{GCP_PROJECT}.{BQ_DATASET}"

    rows_runs = []
    rows_cases = []

    for suite in suites:
        rows_runs.append({
            "pipeline_id": pipeline_meta["pipeline_id"],
            "project_id": pipeline_meta["project_id"],
            "job_name": pipeline_meta["job_name"],
            "ref": pipeline_meta["ref"],
            "commit_sha": pipeline_meta["commit_sha"],
            "suite_name": suite["suite_name"],
            "tests": suite["tests"],
            "passed": suite["passed"],
            "failed": suite["failed"],
            "skipped": suite["skipped"],
            "errors": suite["errors"],
            "duration_s": suite["duration_s"],
            "ingested_at": now,
        })

        for tc in suite["test_cases"]:
            rows_cases.append({
                "pipeline_id": pipeline_meta["pipeline_id"],
                "job_name": pipeline_meta["job_name"],
                "suite_name": suite["suite_name"],
                "test_name": tc["test_name"],
                "classname": tc["classname"],
                "status": tc["status"],
                "duration_s": tc["duration_s"],
                "message": tc["message"],
                "ingested_at": now,
            })

    total = 0

    if rows_runs:
        errors = client.insert_rows_json(f"{dataset_ref}.test_runs", rows_runs)
        if errors:
            print(f"  ❌ BigQuery insert errors (test_runs): {errors}")
        else:
            total += len(rows_runs)
            print(f"  ✅ test_runs: {len(rows_runs)} rows")

    if rows_cases:
        errors = client.insert_rows_json(f"{dataset_ref}.test_cases", rows_cases)
        if errors:
            print(f"  ❌ BigQuery insert errors (test_cases): {errors}")
        else:
            total += len(rows_cases)
            print(f"  ✅ test_cases: {len(rows_cases)} rows")

    return total


# ── Find XMLs ───────────────────────────────────────────────────
def find_junit_xmls(extra_paths: list[str] = None) -> list[str]:
    """Find JUnit XML files from known locations + glob patterns."""
    project_dir = os.environ.get("CI_PROJECT_DIR", ".")
    found = set()

    search_paths = JUNIT_XML_PATHS + (extra_paths or [])

    for pattern in search_paths:
        full_pattern = os.path.join(project_dir, pattern)
        matches = glob.glob(full_pattern, recursive=True)
        for m in matches:
            if os.path.isfile(m) and os.path.getsize(m) > 0:
                found.add(os.path.abspath(m))

    return sorted(found)


# ── Main ────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Collect CI test metrics into BigQuery")
    parser.add_argument("--xml", nargs="*", help="Explicit XML file paths")
    parser.add_argument("--pipeline-id", type=int, help="Override pipeline ID")
    parser.add_argument("--job-name", help="Override job name")
    parser.add_argument("--dry-run", action="store_true", help="Parse XMLs but don't insert")
    args = parser.parse_args()

    print("╔═══════════════════════════════════════╗")
    print("║  CI Metrics Collector — Phase 3       ║")
    print("╚═══════════════════════════════════════╝")

    # Pipeline metadata from CI environment
    pipeline_meta = {
        "pipeline_id": args.pipeline_id or int(os.environ.get("CI_PIPELINE_ID", 0)),
        "project_id": int(os.environ.get("CI_PROJECT_ID", 77555895)),
        "job_name": args.job_name or os.environ.get("CI_JOB_NAME", "unknown"),
        "ref": os.environ.get("CI_COMMIT_REF_NAME", "local"),
        "commit_sha": os.environ.get("CI_COMMIT_SHA", ""),
    }

    print(f"\n📋 Pipeline #{pipeline_meta['pipeline_id']} "
          f"({pipeline_meta['ref']}) "
          f"job={pipeline_meta['job_name']}")

    # Find XML files
    xml_files = args.xml or find_junit_xmls()

    if not xml_files:
        print("\n⚠️  No JUnit XML files found — nothing to collect")
        print("   Searched:", JUNIT_XML_PATHS)
        sys.exit(0)

    print(f"\n📁 Found {len(xml_files)} XML file(s):")

    # Parse all XMLs
    all_suites = []
    total_tests = 0
    total_passed = 0
    total_failed = 0

    for xml_path in xml_files:
        rel_path = os.path.relpath(xml_path, os.environ.get("CI_PROJECT_DIR", "."))
        print(f"\n  📄 {rel_path}")
        try:
            suites = parse_junit_xml(xml_path)
            if suites:
                for s in suites:
                    total_tests += s["tests"]
                    total_passed += s["passed"]
                    total_failed += s["failed"]
                    print(f"     └─ {s['suite_name']}: "
                          f"{s['tests']} tests, "
                          f"{s['passed']} passed, "
                          f"{s['failed']} failed, "
                          f"{s['duration_s']:.1f}s")
                all_suites.extend(suites)
        except Exception as e:
            print(f"     ❌ Parse error: {e}")

    if not all_suites:
        print("\n⚠️  No test suites found in XML files")
        sys.exit(0)

    # Summary
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    print(f"\n📊 Summary: {total_tests} tests, "
          f"{total_passed} passed, "
          f"{total_failed} failed "
          f"({pass_rate:.0f}% pass rate)")

    if args.dry_run:
        print("\n🔍 Dry run — skipping BigQuery insert")
        print(json.dumps({"pipeline": pipeline_meta, "suites_count": len(all_suites)}, indent=2))
        return

    # Insert into BigQuery
    print(f"\n📤 Inserting into BigQuery ({GCP_PROJECT}.{BQ_DATASET})...")
    rows = insert_to_bigquery(all_suites, pipeline_meta)

    if rows > 0:
        print(f"\n✅ Done! {rows} total rows inserted")
    else:
        print("\n⚠️  No rows inserted (check errors above)")
        sys.exit(1)


if __name__ == "__main__":
    main()
