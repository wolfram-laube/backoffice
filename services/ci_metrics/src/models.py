"""Data models for CI metrics ingestion and storage."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


    # noqa: pytest
class TestCase(BaseModel):
    __test__ = False  # prevent pytest collection
    """Individual test case result."""
    name: str
    classname: str = ""
    status: str = Field(description="passed | failed | skipped | error")
    duration_s: float = 0.0
    message: Optional[str] = None


class TestSuiteResult(BaseModel):
    __test__ = False  # prevent pytest collection
    """Aggregated result from a single JUnit XML."""
    suite_name: str
    tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration_s: float = 0.0
    test_cases: list[TestCase] = []


class PipelineMetadata(BaseModel):
    """CI pipeline context."""
    pipeline_id: int
    project_id: int = 77555895
    job_name: str
    ref: str = "main"
    commit_sha: str = ""
    triggered_at: Optional[datetime] = None


class IngestRequest(BaseModel):
    """POST /ingest request body."""
    pipeline: PipelineMetadata
    suites: list[TestSuiteResult]


class IngestResponse(BaseModel):
    """POST /ingest response."""
    status: str = "ok"
    rows_inserted: int = 0
    pipeline_id: int = 0


class MetricsSummary(BaseModel):
    """GET /summary response."""
    total_pipelines: int = 0
    total_test_runs: int = 0
    avg_pass_rate: float = 0.0
    avg_duration_s: float = 0.0
    last_ingested: Optional[datetime] = None
