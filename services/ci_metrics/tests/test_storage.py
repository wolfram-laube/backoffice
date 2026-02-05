"""Tests for JSON file storage backend."""

import json
import pytest
import tempfile

from src.models import IngestRequest, PipelineMetadata, TestSuiteResult, TestCase
from src.storage import JSONFileStore


@pytest.fixture
def store(tmp_path):
    """Create a JSONFileStore with a temporary file."""
    return JSONFileStore(path=str(tmp_path / "test_metrics.json"))


@pytest.fixture
def sample_request():
    return IngestRequest(
        pipeline=PipelineMetadata(
            pipeline_id=1001,
            job_name="test:unit",
            ref="main",
            commit_sha="abc123",
        ),
        suites=[TestSuiteResult(
            suite_name="pytest",
            tests=5,
            passed=4,
            failed=1,
            skipped=0,
            errors=0,
            duration_s=1.23,
            test_cases=[
                TestCase(name="test_ok", classname="t", status="passed", duration_s=0.1),
                TestCase(name="test_fail", classname="t", status="failed", duration_s=0.5, message="assert 1==2"),
            ],
        )],
    )


class TestJSONFileStore:

    @pytest.mark.asyncio
    async def test_insert_returns_row_count(self, store, sample_request):
        rows = await store.insert(sample_request)
        # 1 suite run + 2 test cases = 3 rows
        assert rows == 3

    @pytest.mark.asyncio
    async def test_insert_persists_to_file(self, store, sample_request):
        await store.insert(sample_request)
        data = json.loads(store.path.read_text())
        assert len(data["test_runs"]) == 1
        assert len(data["test_cases"]) == 2

    @pytest.mark.asyncio
    async def test_insert_pipeline_metadata(self, store, sample_request):
        await store.insert(sample_request)
        run = json.loads(store.path.read_text())["test_runs"][0]
        assert run["pipeline_id"] == 1001
        assert run["job_name"] == "test:unit"
        assert run["commit_sha"] == "abc123"

    @pytest.mark.asyncio
    async def test_insert_suite_data(self, store, sample_request):
        await store.insert(sample_request)
        run = json.loads(store.path.read_text())["test_runs"][0]
        assert run["tests"] == 5
        assert run["passed"] == 4
        assert run["failed"] == 1

    @pytest.mark.asyncio
    async def test_summary_empty(self, store):
        summary = await store.get_summary()
        assert summary.total_pipelines == 0
        assert summary.total_test_runs == 0

    @pytest.mark.asyncio
    async def test_summary_after_insert(self, store, sample_request):
        await store.insert(sample_request)
        summary = await store.get_summary()
        assert summary.total_pipelines == 1
        assert summary.total_test_runs == 1
        assert summary.avg_pass_rate == pytest.approx(0.8)  # 4/5
        assert summary.avg_duration_s == pytest.approx(1.23)

    @pytest.mark.asyncio
    async def test_multiple_inserts(self, store, sample_request):
        await store.insert(sample_request)
        # Second pipeline
        req2 = sample_request.model_copy(deep=True)
        req2.pipeline.pipeline_id = 1002
        await store.insert(req2)

        summary = await store.get_summary()
        assert summary.total_pipelines == 2
        assert summary.total_test_runs == 2

    @pytest.mark.asyncio
    async def test_corrupted_file_recovery(self, tmp_path):
        path = tmp_path / "corrupt.json"
        path.write_text("not valid json{{{")
        store = JSONFileStore(path=str(path))
        summary = await store.get_summary()
        assert summary.total_pipelines == 0
