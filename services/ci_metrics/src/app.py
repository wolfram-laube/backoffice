"""CI Metrics Collector — FastAPI application.

Lightweight Cloud Run service that ingests JUnit XML test results
and stores them for trend analysis and observability.

Architecture Decision: INF-001
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import PlainTextResponse

from .models import IngestRequest, IngestResponse, MetricsSummary, PipelineMetadata
from .parser import parse_junit_xml
from .storage import create_store

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

store = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize storage on startup."""
    global store
    store = create_store()
    logger.info(f"CI Metrics Collector v{app.version} started")
    logger.info(f"Storage backend: {store.__class__.__name__}")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="CI Metrics Collector",
    description="Lightweight test observability for Blauweiss CI/CD pipelines",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint for Cloud Run."""
    return {
        "status": "healthy",
        "service": "ci-metrics-collector",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "storage": store.__class__.__name__ if store else "not initialized",
    }


# ---------------------------------------------------------------------------
# Ingest (JSON)
# ---------------------------------------------------------------------------

@app.post("/ingest", response_model=IngestResponse)
async def ingest_json(request: IngestRequest):
    """Ingest pre-parsed test metrics as JSON.

    Used when the CI job has already parsed JUnit XML into structured data.
    """
    try:
        rows = await store.insert(request)
        logger.info(
            f"Ingested pipeline #{request.pipeline.pipeline_id} "
            f"job={request.pipeline.job_name}: {rows} rows"
        )
        return IngestResponse(
            status="ok",
            rows_inserted=rows,
            pipeline_id=request.pipeline.pipeline_id,
        )
    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Ingest (JUnit XML file upload)
# ---------------------------------------------------------------------------

@app.post("/ingest/xml", response_model=IngestResponse)
async def ingest_xml(
    file: UploadFile = File(...),
    pipeline_id: int = Form(...),
    job_name: str = Form(...),
    project_id: int = Form(77555895),
    ref: str = Form("main"),
    commit_sha: str = Form(""),
):
    """Ingest raw JUnit XML file directly.

    Simpler API for CI jobs that just want to upload report.xml without
    pre-parsing. The service handles XML parsing internally.
    """
    try:
        content = await file.read()
        xml_str = content.decode("utf-8")
        suites = parse_junit_xml(xml_str)

        if not suites:
            raise HTTPException(
                status_code=400,
                detail="No test suites found in XML"
            )

        request = IngestRequest(
            pipeline=PipelineMetadata(
                pipeline_id=pipeline_id,
                project_id=project_id,
                job_name=job_name,
                ref=ref,
                commit_sha=commit_sha,
            ),
            suites=suites,
        )

        rows = await store.insert(request)
        logger.info(
            f"Ingested XML pipeline #{pipeline_id} job={job_name}: "
            f"{sum(s.tests for s in suites)} tests, {rows} rows"
        )
        return IngestResponse(
            status="ok",
            rows_inserted=rows,
            pipeline_id=pipeline_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"XML ingest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

@app.get("/summary", response_model=MetricsSummary)
async def get_summary():
    """Get aggregated test metrics summary."""
    try:
        return await store.get_summary()
    except Exception as e:
        logger.error(f"Summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Prometheus Metrics (future-proofing for Option C upgrade)
# ---------------------------------------------------------------------------

@app.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """Prometheus-compatible metrics endpoint.

    Exposes key metrics in Prometheus exposition format for
    future integration with Prometheus/Grafana stack (INF-001 Option C).
    """
    try:
        summary = await store.get_summary()
        lines = [
            "# HELP ci_pipelines_total Total number of pipelines ingested",
            "# TYPE ci_pipelines_total counter",
            f"ci_pipelines_total {summary.total_pipelines}",
            "",
            "# HELP ci_test_runs_total Total number of test suite runs",
            "# TYPE ci_test_runs_total counter",
            f"ci_test_runs_total {summary.total_test_runs}",
            "",
            "# HELP ci_test_pass_rate Average test pass rate",
            "# TYPE ci_test_pass_rate gauge",
            f"ci_test_pass_rate {summary.avg_pass_rate:.4f}",
            "",
            "# HELP ci_test_duration_avg_seconds Average test suite duration",
            "# TYPE ci_test_duration_avg_seconds gauge",
            f"ci_test_duration_avg_seconds {summary.avg_duration_s:.4f}",
            "",
        ]
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Metrics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
