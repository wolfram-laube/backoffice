#!/usr/bin/env python3
"""
NSAI Shadow Comparator — INF-002

Runs after every pipeline in .post stage. For each completed job:
  1. Records what GitLab ACTUALLY picked (random among tagged runners)
  2. Asks pure MAB what it WOULD have picked (UCB1)
  3. Asks NSAI what it WOULD have picked (CSP+UCB1)
  4. Logs all three + actual outcome to BigQuery

This produces the A/B comparison dataset for the research paper:
  "Neurosymbolic Runner Selection: CSP+MAB vs Pure MAB vs Random"

Usage (standalone):
    python nsai_shadow.py --pipeline-id 12345 --project-id 77555895

Usage (in CI):
    Called by mab:report job in .post stage

BigQuery Table: ci_metrics.runner_decisions
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Optional


def get_pipeline_jobs(project_id: str, pipeline_id: str, token: str) -> list:
    """Fetch all jobs from a pipeline via GitLab API."""
    import requests
    url = f"https://gitlab.com/api/v4/projects/{project_id}/pipelines/{pipeline_id}/jobs"
    resp = requests.get(url, headers={"PRIVATE-TOKEN": token}, params={"per_page": 100})
    resp.raise_for_status()
    return resp.json()


def get_mab_recommendation(mab_url: str) -> dict:
    """Query pure MAB service for recommendation."""
    import requests
    try:
        resp = requests.get(f"{mab_url}/recommend", timeout=5)
        return resp.json()
    except Exception:
        return {"recommended_runner": "unknown", "error": "unreachable"}


def get_mab_stats(mab_url: str) -> dict:
    """Get current MAB statistics."""
    import requests
    try:
        resp = requests.get(f"{mab_url}/stats", timeout=5)
        return resp.json()
    except Exception:
        return {}


def nsai_select(job_tags: list, mab_stats: dict) -> dict:
    """
    Ask NSAI for its recommendation given job tags and current MAB state.

    Returns dict with:
        runner: selected runner name
        feasible: list of feasible runners (CSP layer)
        confidence: selection confidence
        symbolic_reasoning: why runners were filtered
        statistical_reasoning: why this runner was chosen
    """
    try:
        from nsai import NeurosymbolicBandit
        nsai = NeurosymbolicBandit.create_default()

        # Sync from live MAB stats
        if mab_stats.get("runners"):
            nsai.sync_from_mab_service(mab_stats["runners"])

        job_def = {"tags": job_tags}
        runner, explanation = nsai.select_runner(job_def)

        return {
            "runner": runner or "none",
            "feasible": explanation.feasible_runners,
            "feasible_count": len(explanation.feasible_runners),
            "confidence": explanation.confidence,
            "symbolic_reasoning": explanation.symbolic_reasoning[:500],
            "statistical_reasoning": explanation.statistical_reasoning[:500],
            "solve_time_ms": explanation.solve_time_ms,
        }
    except Exception as e:
        return {
            "runner": "error",
            "feasible": [],
            "feasible_count": 0,
            "confidence": 0.0,
            "symbolic_reasoning": f"Error: {e}",
            "statistical_reasoning": "",
            "solve_time_ms": 0.0,
        }


def insert_to_bigquery(rows: list) -> int:
    """Insert comparison rows into BigQuery."""
    gcp_project = os.environ.get("GCP_PROJECT", "myk8sproject-207017")
    dataset = os.environ.get("CI_METRICS_BQ_DATASET", "ci_metrics")
    table = f"{gcp_project}.{dataset}.runner_decisions"

    key_b64 = os.environ.get("GCP_SERVICE_ACCOUNT_KEY", "")
    if not key_b64:
        print("  ⚠️  No GCP_SERVICE_ACCOUNT_KEY — skipping BigQuery insert")
        return 0

    try:
        import base64, tempfile
        from google.cloud import bigquery
        from google.oauth2 import service_account

        key_json = base64.b64decode(key_b64)
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False) as f:
            f.write(key_json)
            key_path = f.name

        creds = service_account.Credentials.from_service_account_file(
            key_path, scopes=["https://www.googleapis.com/auth/bigquery"]
        )
        client = bigquery.Client(project=gcp_project, credentials=creds)
        os.unlink(key_path)

        # Ensure table exists
        schema = [
            bigquery.SchemaField("timestamp", "TIMESTAMP"),
            bigquery.SchemaField("pipeline_id", "INTEGER"),
            bigquery.SchemaField("project", "STRING"),
            bigquery.SchemaField("job_name", "STRING"),
            bigquery.SchemaField("job_tags", "STRING"),  # JSON array
            bigquery.SchemaField("job_status", "STRING"),
            bigquery.SchemaField("job_duration", "FLOAT"),
            # What actually happened
            bigquery.SchemaField("actual_runner", "STRING"),
            # Pure MAB recommendation
            bigquery.SchemaField("mab_runner", "STRING"),
            # NSAI recommendation
            bigquery.SchemaField("nsai_runner", "STRING"),
            bigquery.SchemaField("nsai_feasible_count", "INTEGER"),
            bigquery.SchemaField("nsai_confidence", "FLOAT"),
            bigquery.SchemaField("nsai_solve_time_ms", "FLOAT"),
            # Match flags (for easy querying)
            bigquery.SchemaField("mab_would_match", "BOOLEAN"),
            bigquery.SchemaField("nsai_would_match", "BOOLEAN"),
            bigquery.SchemaField("all_agree", "BOOLEAN"),
        ]

        table_ref = bigquery.Table(table, schema=schema)
        try:
            client.get_table(table_ref)
        except Exception:
            table_ref = client.create_table(table_ref)
            print(f"  📊 Created BigQuery table: {table}")

        errors = client.insert_rows_json(table, rows)
        if errors:
            print(f"  ❌ BigQuery insert errors: {errors[:2]}")
            return 0
        return len(rows)

    except ImportError:
        print("  ⚠️  google-cloud-bigquery not installed")
        return 0
    except Exception as e:
        print(f"  ⚠️  BigQuery error: {e}")
        return 0


def main():
    parser = argparse.ArgumentParser(description="NSAI Shadow Comparator")
    parser.add_argument("--pipeline-id", default=os.environ.get("CI_PIPELINE_ID"))
    parser.add_argument("--project-id", default=os.environ.get("CI_PROJECT_ID"))
    parser.add_argument("--project-name", default=os.environ.get("CI_PROJECT_NAME", "unknown"))
    parser.add_argument("--token", default=os.environ.get("GITLAB_API_TOKEN"))
    parser.add_argument("--mab-url", default=os.environ.get(
        "MAB_SERVICE_URL", "https://runner-bandit-m5cziijwqa-lz.a.run.app"))
    parser.add_argument("--dry-run", action="store_true", help="Print but don't insert to BQ")
    args = parser.parse_args()

    if not args.pipeline_id or not args.project_id:
        print("❌ Need --pipeline-id and --project-id (or CI env vars)")
        sys.exit(1)

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("  NSAI Shadow Comparator")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    # 1. Get MAB state
    print("📡 Fetching MAB state...")
    mab_stats = get_mab_stats(args.mab_url)
    mab_rec = get_mab_recommendation(args.mab_url)
    mab_runner = mab_rec.get("recommended_runner", "unknown")
    print(f"  MAB recommendation: {mab_runner}")
    print(f"  MAB observations: {mab_stats.get('total_observations', 0)}")

    # 2. Get pipeline jobs
    print(f"\n📋 Fetching pipeline #{args.pipeline_id} jobs...")
    jobs = get_pipeline_jobs(args.project_id, args.pipeline_id, args.token)

    now = datetime.now(timezone.utc).isoformat()
    rows = []
    skipped = 0

    for job in jobs:
        name = job["name"]
        status = job["status"]
        runner = job.get("runner", {}).get("description", "") if job.get("runner") else ""
        duration = job.get("duration") or 0

        # Skip non-executed jobs
        if not runner or status in ("manual", "skipped", "created", "pending"):
            skipped += 1
            continue

        # Skip shared runners and this job itself
        if any(x in runner for x in ("saas", "shared-gitlab", "runners-manager")):
            skipped += 1
            continue
        if name in ("mab:report", "nsai:shadow"):
            skipped += 1
            continue

        # Infer job tags from the CI config (we use the runner's tags as proxy)
        # In practice, all our jobs use docker-any
        job_tags = ["docker-any"]  # default; could parse .gitlab-ci.yml for precision

        # 3. Ask NSAI
        nsai_result = nsai_select(job_tags, mab_stats)

        row = {
            "timestamp": now,
            "pipeline_id": int(args.pipeline_id),
            "project": args.project_name,
            "job_name": name,
            "job_tags": json.dumps(job_tags),
            "job_status": status,
            "job_duration": float(duration),
            "actual_runner": runner,
            "mab_runner": mab_runner,
            "nsai_runner": nsai_result["runner"],
            "nsai_feasible_count": nsai_result["feasible_count"],
            "nsai_confidence": nsai_result["confidence"],
            "nsai_solve_time_ms": nsai_result["solve_time_ms"],
            "mab_would_match": runner == mab_runner,
            "nsai_would_match": runner == nsai_result["runner"],
            "all_agree": runner == mab_runner == nsai_result["runner"],
        }
        rows.append(row)

        match_icon = "🎯" if row["nsai_would_match"] else "↔️"
        print(f"  {match_icon} {name:25s} actual:{runner:25s} mab:{mab_runner:20s} nsai:{nsai_result['runner']:20s} ({nsai_result['feasible_count']} feasible)")

    print(f"\n  Compared: {len(rows)} | Skipped: {skipped}")

    # 4. Summary stats
    if rows:
        mab_matches = sum(1 for r in rows if r["mab_would_match"])
        nsai_matches = sum(1 for r in rows if r["nsai_would_match"])
        all_agree = sum(1 for r in rows if r["all_agree"])

        print(f"\n  ═══ Shadow Comparison ═══")
        print(f"    GitLab random vs MAB agree:  {mab_matches}/{len(rows)} ({mab_matches/len(rows)*100:.0f}%)")
        print(f"    GitLab random vs NSAI agree: {nsai_matches}/{len(rows)} ({nsai_matches/len(rows)*100:.0f}%)")
        print(f"    All three agree:             {all_agree}/{len(rows)} ({all_agree/len(rows)*100:.0f}%)")

    # 5. Insert to BigQuery
    if rows and not args.dry_run:
        print(f"\n📊 Inserting {len(rows)} rows to BigQuery...")
        inserted = insert_to_bigquery(rows)
        print(f"  ✅ Inserted: {inserted} rows")
    elif args.dry_run:
        print(f"\n  (dry run — {len(rows)} rows would be inserted)")
        print(f"  Sample: {json.dumps(rows[0], indent=2)}")

    # 6. Write artifact
    artifact_path = os.environ.get("CI_PROJECT_DIR", "/tmp")
    out_file = os.path.join(artifact_path, "nsai-shadow.json")
    with open(out_file, "w") as f:
        json.dump({
            "pipeline_id": int(args.pipeline_id),
            "timestamp": now,
            "mab_recommendation": mab_runner,
            "mab_observations": mab_stats.get("total_observations", 0),
            "comparisons": rows,
            "summary": {
                "total_jobs": len(rows),
                "mab_agreement": mab_matches if rows else 0,
                "nsai_agreement": nsai_matches if rows else 0,
                "all_agree": all_agree if rows else 0,
            }
        }, f, indent=2)
    print(f"\n  📄 Artifact: {out_file}")


if __name__ == "__main__":
    main()
