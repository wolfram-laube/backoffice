# Handover: CI Metrics Collector — 05.02.2026

## Summary

Completed full implementation of CI Metrics Collector (Phases 2-4) per ADR INF-001.
Test results from GitLab CI pipelines are now automatically collected and visualized.

## Merge Details

| Item | Value |
|------|-------|
| MR | !15 |
| Merge Commit | `66ef740d` |
| Squash Commit | `d142e333` |
| Issue | #40 (closed) |
| Merged | 2026-02-05 16:49 UTC |

## What Was Delivered

### Phase 2: BigQuery Setup
- **Dataset:** `myk8sproject-207017.ci_metrics` (europe-north1)
- **Tables:**
  - `test_runs` — 13 columns, partitioned by `ingested_at`
  - `test_cases` — 9 columns, partitioned by `ingested_at`
- **Auth:** SA key regenerated (`2d328d70...`), IAM roles granted (dataEditor, user, jobUser)
- **Script:** `scripts/setup-bigquery.sh` — one-time local setup

### Phase 3: Collect Jobs
- **Script:** `scripts/collect-metrics.py`
  - Finds JUnit XML reports from CI artifacts
  - Parses test results (reuses parser logic from Phase 1)
  - Inserts directly into BigQuery via SA key
- **CI Jobs:**
  - `ci-metrics:collect` — after `test:unit` (main + MRs)
  - `ci-metrics:collect:nsai` — after `test:nsai:unit` + `test:nsai:notebooks`
  - Both `allow_failure: true` — never blocks pipeline

### Phase 4: Dashboard
- **Generator:** `scripts/generate-dashboard.py`
  - Queries BigQuery for summary, trends, failures, flaky tests
  - Generates static HTML with Chart.js charts
- **Dashboard Features:**
  - 5 KPI cards (pipelines, pass rate, failures, duration, last ingested)
  - Pass rate trend chart (30 days)
  - Duration + test count trend chart
  - Job breakdown table
  - Recent failures table
  - Flaky test detection (failed in multiple pipelines)
  - Pipeline history (last 50)
- **CI Job:** `ci-metrics:dashboard` — auto-commits updated HTML to main
- **Portal:** Added under 🧠 Services → 📊 CI Metrics

### Additional Fixes
- Fixed `tests.yml` and `nsai-tests.yml` artifact paths
  - Added `paths: - report.xml` alongside `reports: junit:`
  - Ensures downstream `needs:` jobs receive the XML files

## Files Changed

```
.gitlab/ci-metrics.yml           # NEW — 7 CI jobs
.gitlab/tests.yml                # FIX — artifact paths
.gitlab/nsai-tests.yml           # FIX — artifact paths
.gitlab-ci.yml                   # ADD — include ci-metrics
scripts/collect-metrics.py       # NEW — JUnit XML → BigQuery
scripts/generate-dashboard.py    # NEW — BigQuery → HTML
scripts/setup-bigquery.sh        # NEW — one-time GCP setup
docs/ci-dashboard.html           # NEW — static dashboard
mkdocs.yml                       # ADD — nav entry
```

## Verification

Pipeline #2308418266 verified end-to-end:
1. `test:unit` ✅ (35s) — generated `report.xml`
2. `ci-metrics:collect` ✅ (25s) — 168 tests, 100% pass rate → BigQuery
3. `ci-metrics:dashboard` — auto-committed `924e372a`

## Access Points

- **Dashboard:** https://wolfram_laube.gitlab.io/blauweiss_llc/ops/backoffice/ci-dashboard.html
- **BigQuery Console:** https://console.cloud.google.com/bigquery?project=myk8sproject-207017&ws=!1m4!1m3!3m2!1smyk8sproject-207017!2sci_metrics
- **Issue:** https://gitlab.com/wolfram_laube/blauweiss_llc/ops/backoffice/-/issues/40
- **MR:** https://gitlab.com/wolfram_laube/blauweiss_llc/ops/backoffice/-/merge_requests/15

## Blockers Resolved

- **SA Key expired** — regenerated via `setup-bigquery.sh` on Yoga (Heimdall)
- **Artifact paths** — JUnit XMLs weren't passed to downstream jobs; fixed by adding `paths:` to artifacts

## Next Steps (Optional)

- [ ] Schedule dashboard regeneration (currently only on main pushes)
- [ ] Add Slack notification for low pass rates
- [ ] Consider Grafana Cloud upgrade (INF-001 Option C) for real-time monitoring
