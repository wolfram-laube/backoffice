# Handover: Runner Intelligence Architecture — 2026-02-07

## Session Summary

Diagnosed and repaired the complete runner intelligence stack:
three independent systems (fallback, MAB, NSAI) that were built
but never integrated. Connected them into a working pipeline with
NSAI shadow comparator for research paper evaluation data.

## What Was Done

### Phase 1: Runner Fleet Expansion
- Registered all 11 runners for all 5 projects (40 registrations)
- Fixed Nordic tags: added `shell-any`, `any-runner`, `gcp-any`
- Verified 10 online, 1 offline (Nordic K8s)

### Phase 2: Dead Tag Elimination
- `gcp-shell` → `shell-any` (ci-automation.yml)
- `gcp-shell` → `nordic` (k3s-setup.yml)
- `gcp-docker` → `nordic` (fix-shell-runner.yml)
- `local-shell` removed (runner-fallback.yml rewritten)

### Phase 3: Runner Fallback v4
- Complete rewrite of `.gitlab/runner-fallback.yml`
- Uses real tags (`docker-any`, `shell-any`, `k8s-any`)
- Fleet health check: healthy / degraded / down states
- Clean separation from MAB selection layer

### Phase 4: MAB Integration v3
- Passive pipeline-level reporting (no per-job changes needed)
- `mab:report` in `.post` stage queries all jobs via GitLab API
- Switched from alpine to python:3.11-slim for NSAI support
- **MAB is now learning**: 20 observations from real pipelines

### Phase 5: NSAI v0.4.0
- Ontology: 4 → 11 runners (Docker + Shell + K8s)
- Parser: 16 → 36 tag mappings (full fleet taxonomy)
- All runner IDs populated
- Tests: 60/60 green (19 ontology + 41 integration)
- Version bump: 0.3.0 → 0.4.0

### Phase 6: NSAI Shadow Comparator
- `scripts/nsai_shadow.py` — runs after every pipeline
- Compares: GitLab (random) vs MAB (UCB1) vs NSAI (CSP+UCB1)
- Logs to BigQuery: `ci_metrics.runner_decisions`
- Produces `nsai-shadow.json` artifact (90 days retention)
- Successfully tested against pipeline #2311467900

## Commits

| Hash | Description |
|------|-------------|
| `dd06794e` | feat(infra): runner intelligence architecture [INF-002] — 12 files |
| `f924d147` | feat(nsai): shadow comparator for A/B evaluation [INF-002] — 3 files |
| *(this)* | docs: INF-002 update, NSAI README v0.4.0, handover |

## Current MAB State

```
Algorithm: UCB1  |  Observations: 20
Runner                          Pulls  Success  Avg Duration
gitlab-runner-nordic              11     90.9%       22s
Mac Docker Runner                  1      0.0%       15s  ← Docker down!
Mac2 Docker Runner                 4     75.0%       84s
Linux Yoga Docker Runner           2    100.0%        0s  ← rising star
```

## Known Issues

| Issue | Status | Notes |
|-------|--------|-------|
| `ci-metrics:dashboard` fails | ❌ | git checkout conflict (deeper than our fix) |
| `mab:report` didn't run in Pipeline #2311467900 | ⚠️ | Pipeline ended as `manual` before `.post` stage |
| Mac Docker Runner: 0% success | ⚠️ | Docker Desktop not running on Mac |
| Nordic K8s Runner offline | ⚠️ | k3s not active on GCP VM |
| NSAI shadow: all jobs assumed `docker-any` | 📋 | Could parse actual tags from CI config |

## Files Changed (this session)

```
.gitlab/runner-fallback.yml          ← v4 rewrite
.gitlab/mab-integration.yml          ← v3 with NSAI shadow
.gitlab/ci-automation.yml            ← gcp-shell → shell-any
.gitlab/k3s-setup.yml                ← gcp-shell → nordic
.gitlab/fix-shell-runner.yml         ← gcp-docker → nordic
.gitlab/ci-metrics.yml               ← git checkout fix
scripts/nsai_shadow.py               ← NEW: shadow comparator
services/nsai/__init__.py            ← v0.4.0
services/nsai/pyproject.toml         ← v0.4.0
services/nsai/ontology/runner_ontology.py  ← 11 runners
services/nsai/parser/job_parser.py   ← 36 tag mappings
services/nsai/tests/test_nsai_integration.py  ← 41 tests
services/nsai/tests/test_ontology.py ← 19 tests
services/nsai/README.md              ← shadow mode docs
docs/adr/infrastructure/INF-002-runner-intelligence.md  ← shadow section
docs/adr/README.md                   ← INF-002 listed
```

## Next Steps

1. **Verify mab:report runs** — next `main` commit should trigger `.post` stage properly
2. **Start Docker Desktop on Mac** — Mac Docker Runner will start getting observations
3. **BigQuery table creation** — happens automatically on first successful shadow run
4. **Paper evaluation notebook** — query BigQuery data after ~50 pipelines for meaningful statistics
5. **Consider**: promote NSAI from shadow → active mode via child pipelines
