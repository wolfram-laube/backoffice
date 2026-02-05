# CI Metrics Collector

Lightweight Cloud Run service that ingests JUnit XML test results and stores them for trend analysis.

> **ADR:** [INF-001 — CI/CD Test Observability](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/corporate/-/blob/main/docs/adr/infrastructure/INF-001-ci-test-observability.md)

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/ingest` | Ingest pre-parsed JSON metrics |
| POST | `/ingest/xml` | Upload raw JUnit XML |
| GET | `/summary` | Aggregated test metrics |
| GET | `/metrics` | Prometheus exposition format |

## Quick Start

```bash
# Local development
cd services/ci_metrics
pip install -r requirements.txt
METRICS_BACKEND=json uvicorn src.app:app --reload --port 8080

# Run tests
pytest tests/ -v
```

## CI Usage

```bash
# Upload JUnit XML from CI job
curl -X POST "${CI_METRICS_URL}/ingest/xml" \
  -F "file=@report.xml" \
  -F "pipeline_id=${CI_PIPELINE_ID}" \
  -F "job_name=${CI_JOB_NAME}" \
  -F "ref=${CI_COMMIT_REF_NAME}" \
  -F "commit_sha=${CI_COMMIT_SHA}"
```

## Storage Backends

| Backend | Config | Use Case |
|---------|--------|----------|
| JSON File | `METRICS_BACKEND=json` | Development, fallback |
| BigQuery | `METRICS_BACKEND=bigquery` | Production |
| Auto | `METRICS_BACKEND=auto` | BigQuery if available, else JSON |

## Architecture

```
CI Pipeline → JUnit XML → POST /ingest/xml → Parser → Storage → GET /summary
                                                                → GET /metrics (Prometheus)
```

## Related

- [Issue #40](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/backoffice/-/issues/40) — Implementation backlog
- [ADR INF-001](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/corporate/-/blob/main/docs/adr/infrastructure/INF-001-ci-test-observability.md) — Decision record
- [runner_bandit](../runner_bandit/) — Sibling Cloud Run service
