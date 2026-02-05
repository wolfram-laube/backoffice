"""Tests for the FastAPI application endpoints."""

import pytest
from fastapi.testclient import TestClient

from src.app import app


@pytest.fixture
def client():
    """Create test client."""
    with TestClient(app) as c:
        yield c


SAMPLE_JUNIT_XML = """<?xml version="1.0" encoding="utf-8"?>
<testsuite name="pytest" errors="0" failures="0" skipped="1" tests="3" time="0.330">
  <testcase classname="tests.test_unit" name="test_one" time="0.100"/>
  <testcase classname="tests.test_unit" name="test_two" time="0.200"/>
  <testcase classname="tests.test_unit" name="test_skip" time="0.001">
    <skipped message="not ready"/>
  </testcase>
</testsuite>"""


class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_health_has_status(self, client):
        data = client.get("/health").json()
        assert data["status"] == "healthy"
        assert data["service"] == "ci-metrics-collector"
        assert "version" in data
        assert "storage" in data


class TestIngestJSON:

    def test_ingest_valid(self, client):
        payload = {
            "pipeline": {
                "pipeline_id": 12345,
                "job_name": "test:unit",
            },
            "suites": [{
                "suite_name": "pytest",
                "tests": 10,
                "passed": 9,
                "failed": 1,
                "skipped": 0,
                "errors": 0,
                "duration_s": 1.5,
                "test_cases": [],
            }],
        }
        resp = client.post("/ingest", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["pipeline_id"] == 12345
        assert data["rows_inserted"] >= 1

    def test_ingest_missing_pipeline(self, client):
        resp = client.post("/ingest", json={"suites": []})
        assert resp.status_code == 422


class TestIngestXML:

    def test_ingest_xml_upload(self, client):
        resp = client.post(
            "/ingest/xml",
            files={"file": ("report.xml", SAMPLE_JUNIT_XML, "text/xml")},
            data={
                "pipeline_id": 99999,
                "job_name": "test:nsai:unit",
                "ref": "main",
                "commit_sha": "abc123",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["pipeline_id"] == 99999
        assert data["rows_inserted"] >= 1

    def test_ingest_xml_empty(self, client):
        resp = client.post(
            "/ingest/xml",
            files={"file": ("empty.xml", "<root/>", "text/xml")},
            data={"pipeline_id": 1, "job_name": "test"},
        )
        assert resp.status_code == 400


class TestSummary:

    def test_summary_returns_200(self, client):
        resp = client.get("/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_pipelines" in data
        assert "avg_pass_rate" in data


class TestPrometheusMetrics:

    def test_metrics_returns_text(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "ci_pipelines_total" in resp.text
        assert "ci_test_pass_rate" in resp.text
        assert "ci_test_duration_avg_seconds" in resp.text
