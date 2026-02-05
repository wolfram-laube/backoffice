"""Storage backend for CI metrics.

Supports BigQuery (production) and in-memory/JSON (development).
"""

import json
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from .models import IngestRequest, MetricsSummary

logger = logging.getLogger(__name__)


class MetricsStore(Protocol):
    """Storage backend protocol."""

    async def insert(self, request: IngestRequest) -> int:
        """Insert metrics, return number of rows inserted."""
        ...

    async def get_summary(self) -> MetricsSummary:
        """Get aggregated summary of all stored metrics."""
        ...


class JSONFileStore:
    """Simple JSON file store for development and fallback.

    Stores all metrics in a single JSON file. Good for small-scale
    usage and when BigQuery is not configured.
    """

    def __init__(self, path: str = "/data/metrics.json"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except (json.JSONDecodeError, OSError):
                logger.warning("Corrupted metrics file, starting fresh")
        return {"test_runs": [], "test_cases": []}

    def _save(self):
        self.path.write_text(json.dumps(self._data, indent=2, default=str))

    async def insert(self, request: IngestRequest) -> int:
        rows = 0
        now = datetime.now(timezone.utc).isoformat()

        for suite in request.suites:
            self._data["test_runs"].append({
                "pipeline_id": request.pipeline.pipeline_id,
                "project_id": request.pipeline.project_id,
                "job_name": request.pipeline.job_name,
                "ref": request.pipeline.ref,
                "commit_sha": request.pipeline.commit_sha,
                "suite_name": suite.suite_name,
                "tests": suite.tests,
                "passed": suite.passed,
                "failed": suite.failed,
                "skipped": suite.skipped,
                "errors": suite.errors,
                "duration_s": suite.duration_s,
                "ingested_at": now,
            })
            rows += 1

            for tc in suite.test_cases:
                self._data["test_cases"].append({
                    "pipeline_id": request.pipeline.pipeline_id,
                    "job_name": request.pipeline.job_name,
                    "suite_name": suite.suite_name,
                    "test_name": tc.name,
                    "classname": tc.classname,
                    "status": tc.status,
                    "duration_s": tc.duration_s,
                    "message": tc.message,
                    "ingested_at": now,
                })
                rows += 1

        self._save()
        return rows

    async def get_summary(self) -> MetricsSummary:
        runs = self._data.get("test_runs", [])
        if not runs:
            return MetricsSummary()

        pipeline_ids = set(r["pipeline_id"] for r in runs)
        total_tests = sum(r["tests"] for r in runs)
        total_passed = sum(r["passed"] for r in runs)
        total_duration = sum(r["duration_s"] for r in runs)

        return MetricsSummary(
            total_pipelines=len(pipeline_ids),
            total_test_runs=len(runs),
            avg_pass_rate=total_passed / total_tests if total_tests > 0 else 0.0,
            avg_duration_s=total_duration / len(runs) if runs else 0.0,
            last_ingested=runs[-1].get("ingested_at"),
        )


class BigQueryStore:
    """BigQuery storage backend for production.

    Requires google-cloud-bigquery and GOOGLE_APPLICATION_CREDENTIALS.
    Falls back to JSONFileStore if BigQuery is unavailable.
    """

    def __init__(self, project: str = "myk8sproject-207017", dataset: str = "ci_metrics"):
        self.project = project
        self.dataset = dataset
        self._client = None
        self._fallback = None

        try:
            from google.cloud import bigquery
            self._client = bigquery.Client(project=project)
            self._ensure_dataset()
            logger.info(f"BigQuery connected: {project}.{dataset}")
        except Exception as e:
            logger.warning(f"BigQuery unavailable ({e}), using JSON fallback")
            self._fallback = JSONFileStore()

    def _ensure_dataset(self):
        """Create dataset and tables if they don't exist."""
        from google.cloud import bigquery

        dataset_ref = f"{self.project}.{self.dataset}"
        try:
            self._client.get_dataset(dataset_ref)
        except Exception:
            ds = bigquery.Dataset(dataset_ref)
            ds.location = "europe-north1"
            self._client.create_dataset(ds, exists_ok=True)
            logger.info(f"Created dataset {dataset_ref}")

        # test_runs table
        runs_schema = [
            bigquery.SchemaField("pipeline_id", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("project_id", "INTEGER"),
            bigquery.SchemaField("job_name", "STRING"),
            bigquery.SchemaField("ref", "STRING"),
            bigquery.SchemaField("commit_sha", "STRING"),
            bigquery.SchemaField("suite_name", "STRING"),
            bigquery.SchemaField("tests", "INTEGER"),
            bigquery.SchemaField("passed", "INTEGER"),
            bigquery.SchemaField("failed", "INTEGER"),
            bigquery.SchemaField("skipped", "INTEGER"),
            bigquery.SchemaField("errors", "INTEGER"),
            bigquery.SchemaField("duration_s", "FLOAT"),
            bigquery.SchemaField("ingested_at", "TIMESTAMP"),
        ]
        runs_table = bigquery.Table(f"{dataset_ref}.test_runs", schema=runs_schema)
        runs_table.time_partitioning = bigquery.TimePartitioning(field="ingested_at")
        self._client.create_table(runs_table, exists_ok=True)

        # test_cases table
        cases_schema = [
            bigquery.SchemaField("pipeline_id", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("job_name", "STRING"),
            bigquery.SchemaField("suite_name", "STRING"),
            bigquery.SchemaField("test_name", "STRING"),
            bigquery.SchemaField("classname", "STRING"),
            bigquery.SchemaField("status", "STRING"),
            bigquery.SchemaField("duration_s", "FLOAT"),
            bigquery.SchemaField("message", "STRING"),
            bigquery.SchemaField("ingested_at", "TIMESTAMP"),
        ]
        cases_table = bigquery.Table(f"{dataset_ref}.test_cases", schema=cases_schema)
        cases_table.time_partitioning = bigquery.TimePartitioning(field="ingested_at")
        self._client.create_table(cases_table, exists_ok=True)

    async def insert(self, request: IngestRequest) -> int:
        if self._fallback:
            return await self._fallback.insert(request)

        from datetime import datetime, timezone
        rows_runs = []
        rows_cases = []
        now = datetime.now(timezone.utc).isoformat()

        for suite in request.suites:
            rows_runs.append({
                "pipeline_id": request.pipeline.pipeline_id,
                "project_id": request.pipeline.project_id,
                "job_name": request.pipeline.job_name,
                "ref": request.pipeline.ref,
                "commit_sha": request.pipeline.commit_sha,
                "suite_name": suite.suite_name,
                "tests": suite.tests,
                "passed": suite.passed,
                "failed": suite.failed,
                "skipped": suite.skipped,
                "errors": suite.errors,
                "duration_s": suite.duration_s,
                "ingested_at": now,
            })

            for tc in suite.test_cases:
                rows_cases.append({
                    "pipeline_id": request.pipeline.pipeline_id,
                    "job_name": request.pipeline.job_name,
                    "suite_name": suite.suite_name,
                    "test_name": tc.name,
                    "classname": tc.classname,
                    "status": tc.status,
                    "duration_s": tc.duration_s,
                    "message": tc.message,
                    "ingested_at": now,
                })

        total = 0
        dataset_ref = f"{self.project}.{self.dataset}"

        if rows_runs:
            errors = self._client.insert_rows_json(f"{dataset_ref}.test_runs", rows_runs)
            if errors:
                logger.error(f"BigQuery insert errors (test_runs): {errors}")
            total += len(rows_runs)

        if rows_cases:
            errors = self._client.insert_rows_json(f"{dataset_ref}.test_cases", rows_cases)
            if errors:
                logger.error(f"BigQuery insert errors (test_cases): {errors}")
            total += len(rows_cases)

        return total

    async def get_summary(self) -> MetricsSummary:
        if self._fallback:
            return await self._fallback.get_summary()

        query = f"""
        SELECT
            COUNT(DISTINCT pipeline_id) as total_pipelines,
            COUNT(*) as total_test_runs,
            SAFE_DIVIDE(SUM(passed), SUM(tests)) as avg_pass_rate,
            AVG(duration_s) as avg_duration_s,
            MAX(ingested_at) as last_ingested
        FROM `{self.project}.{self.dataset}.test_runs`
        """
        result = list(self._client.query(query).result())
        if result:
            row = result[0]
            return MetricsSummary(
                total_pipelines=row.total_pipelines or 0,
                total_test_runs=row.total_test_runs or 0,
                avg_pass_rate=float(row.avg_pass_rate or 0),
                avg_duration_s=float(row.avg_duration_s or 0),
                last_ingested=row.last_ingested,
            )
        return MetricsSummary()


def create_store() -> MetricsStore:
    """Factory: creates the appropriate storage backend."""
    backend = os.environ.get("METRICS_BACKEND", "auto")

    if backend == "bigquery":
        return BigQueryStore()
    elif backend == "json":
        return JSONFileStore()
    else:  # auto
        try:
            return BigQueryStore()
        except Exception:
            logger.info("Auto-detected: using JSON file store")
            return JSONFileStore()
