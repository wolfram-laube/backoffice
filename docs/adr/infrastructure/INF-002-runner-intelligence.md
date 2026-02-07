# INF-002: Runner Intelligence Architecture

| Field     | Value                                               |
|-----------|-----------------------------------------------------|
| Status    | **Accepted**                                        |
| Date      | 2026-02-07                                          |
| Author    | Wolfram Laube                                       |
| Tags      | infrastructure, ci-cd, runners, mab, nsai           |
| Refs      | AI-001, INF-001, GOV-001                            |

## Context

Our CI/CD runner fleet has grown to 11 runners across 4 machines and 3 executor
types (Docker, Shell, Kubernetes), serving 5 GitLab projects. Three independent
systems were built to manage them, but never integrated:

1. **runner-fallback.yml** — Availability checking with GCP auto-start
2. **mab-integration.yml** — Multi-Armed Bandit for learning optimal selection
3. **services/nsai/** — Neurosymbolic reasoning for constraint-based selection

As of 2026-02-07, all three are broken:

| System         | Problem                                                |
|----------------|--------------------------------------------------------|
| Fallback       | Searches for `local-shell`, `gcp-shell` — tags that no runner has |
| MAB            | `.mab-enabled` template exists but 0 jobs extend it → 0 observations |
| NSAI Ontology  | Knows 4 Docker runners, missing 7 (Shell + K8s)       |

Additionally:
- Nordic runner was only registered for 2 of 5 projects
- Tag taxonomy inconsistent (Nordic missing `shell-any`, `any-runner`)
- `ci-metrics:dashboard` job fails due to git checkout conflict

## Decision

### Separation of Concerns

Three layers, three responsibilities:

```
┌─────────────────────────────────────────────────┐
│  AVAILABILITY  (runner-fallback.yml)             │
│  "Is anyone alive?"                              │
│  → Checks docker-any/shell-any/k8s-any online    │
│  → Starts GCP VM if fleet is down                │
│  → Runs in .pre stage                            │
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│  LEARNING  (mab-integration.yml)                 │
│  "Who performs best?"                            │
│  → Reports ALL job outcomes to MAB (passive)     │
│  → Queries MAB for recommendation (active)       │
│  → Runs in .post stage (report) / .pre (recommend)│
└──────────────────────┬──────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────┐
│  REASONING  (services/nsai/)                     │
│  "Why that one?"                                 │
│  → CSP: feasible set from hard constraints       │
│  → MAB: optimal selection from soft preferences  │
│  → Ontology: 11 runners, 3 executors, 4 machines │
└─────────────────────────────────────────────────┘
```

### Tag Taxonomy (Source of Truth)

Executor-level tags (use in `tags:` for jobs):

| Tag          | Runners                              | Use for                    |
|--------------|--------------------------------------|----------------------------|
| `docker-any` | Nordic, Mac, Mac2, Linux Yoga (4)   | Most CI jobs               |
| `shell-any`  | Nordic, Mac, Mac2, Linux Yoga (4)   | Jobs needing host access   |
| `k8s-any`    | Mac, Mac2, Linux Yoga, Nordic* (4)  | Kubernetes workloads       |
| `any-runner`  | All 11 runners                      | Executor-agnostic jobs     |

Machine-level tags (for pinning to specific hardware):

| Tag          | Runners                    |
|--------------|----------------------------|
| `mac-any`    | Mac Docker/Shell/K8s       |
| `linux-any`  | Linux Yoga Docker/Shell/K8s|
| `gcp-any`    | Nordic Docker, Nordic K8s  |
| `nordic`     | Nordic Docker specifically |

Dead tags removed: `local-shell`, `gcp-shell`, `gcp-docker`.

### MAB Integration: Passive Reporting

Instead of requiring every job to `extends: .mab-enabled` (invasive, fragile),
a single `mab:report` job in `.post` stage queries ALL pipeline jobs via the
GitLab API and bulk-reports outcomes. Zero changes to existing jobs.

```
Pipeline runs normally
  → test:unit runs on [some runner]
  → pages runs on [some runner]
  → billing runs on [some runner]
  → .post: mab:report queries all jobs → reports to MAB service
```

### Fleet Registration

All 11 runners registered for all 5 projects:

| Runner                    | backoffice | corporate | crm | clarissa | portal |
|---------------------------|:----------:|:---------:|:---:|:--------:|:------:|
| gitlab-runner-nordic      | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mac Docker Runner         | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mac2 Docker Runner        | ✅ | ✅ | ✅ | ✅ | ✅ |
| Linux Yoga Docker Runner  | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mac Shell Runner          | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mac2 Shell Runner         | ✅ | ✅ | ✅ | ✅ | ✅ |
| Linux Yoga Shell Runner   | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mac K8s Runner            | ✅ | ✅ | ✅ | ✅ | ✅ |
| Mac2 K8s Runner           | ✅ | ✅ | ✅ | ✅ | ✅ |
| Linux Yoga K8s Runner     | ✅ | ✅ | ✅ | ✅ | ✅ |
| Nordic K8s Runner         | ✅ | ✅ | ✅ | ✅ | ✅ |

## Changes

| File | Change |
|------|--------|
| `.gitlab/runner-fallback.yml` | v4: correct tags, fleet health check, clean separation |
| `.gitlab/mab-integration.yml` | v2→v3: passive reporting + NSAI shadow comparator |
| `.gitlab/ci-automation.yml` | `gcp-shell` → `shell-any` |
| `.gitlab/k3s-setup.yml` | `gcp-shell` → `nordic` |
| `.gitlab/fix-shell-runner.yml` | `gcp-docker` → `nordic` |
| `.gitlab/ci-metrics.yml` | Fix git checkout conflict in dashboard job |
| `services/nsai/ontology/runner_ontology.py` | 4 → 11 runners, add IDs, K8s + Shell |
| `services/nsai/parser/job_parser.py` | 16 → 36 tag mappings (full fleet taxonomy) |
| `services/nsai/__init__.py` | v0.3.0 → v0.4.0 |
| `services/nsai/pyproject.toml` | v0.2.0 → v0.4.0 |
| `services/nsai/tests/*` | Updated for 11-runner fleet (60/60 green) |
| `scripts/nsai_shadow.py` | **NEW:** Shadow comparator for A/B evaluation |
| Nordic runner tags | Added `shell-any`, `any-runner`, `gcp-any` |
| Runner registration | All 11 runners → all 5 projects |

### NSAI Shadow Comparator

NSAI runs in **shadow mode** — it doesn't route jobs, but compares what
three strategies *would have* picked for every completed job:

```
Pipeline completes
  ↓
.post: mab:report
  ├─ 1. Report outcomes to MAB Cloud Run (as before)
  ├─ 2. For each job, compare:
  │     ┌────────────┬──────────────────────────────────┐
  │     │ Strategy   │ Selection Method                 │
  │     ├────────────┼──────────────────────────────────┤
  │     │ GitLab     │ Random (tag-matching)            │
  │     │ MAB        │ UCB1 (exploration/exploitation)  │
  │     │ NSAI       │ CSP filter → UCB1                │
  │     └────────────┴──────────────────────────────────┘
  ├─ 3. Log to BigQuery: ci_metrics.runner_decisions
  └─ 4. Artifact: nsai-shadow.json (90 days)
```

**BigQuery Schema** (`ci_metrics.runner_decisions`):

| Column | Type | Description |
|--------|------|-------------|
| `actual_runner` | STRING | What GitLab randomly picked |
| `mab_runner` | STRING | What pure MAB would pick |
| `nsai_runner` | STRING | What CSP+MAB would pick |
| `nsai_feasible_count` | INTEGER | Runners passing CSP filter |
| `nsai_confidence` | FLOAT | UCB1 confidence score |
| `mab_would_match` | BOOLEAN | MAB agrees with GitLab? |
| `nsai_would_match` | BOOLEAN | NSAI agrees with GitLab? |
| `job_status` | STRING | success / failed |
| `job_duration` | FLOAT | Seconds |

This dataset enables the research paper evaluation:
*"Neurosymbolic Runner Selection: CSP+MAB vs Pure MAB vs Random"*

## Consequences

### Positive

- MAB starts learning from real pipeline data immediately (passive, no job changes)
- Fallback actually works (uses tags that exist)
- NSAI ontology reflects reality (11 runners, not 4)
- All projects can use all runners (balanced load)
- Clean separation: availability ≠ selection ≠ reasoning
- **Shadow mode produces real A/B evaluation data for research paper**
- **BigQuery table auto-created on first pipeline run**

### Negative / Trade-offs

- `mab:report` adds ~30s to every pipeline (MAB report + NSAI shadow)
- MAB service needs to handle 11 runners (was 4) — UCB1 scales fine
- Nordic K8s Runner still offline (k3s not running)
- NSAI shadow requires `GIT_STRATEGY: clone` (needs source for `pip install -e`)

### Future Work

- Dynamic runner selection via child pipelines (MAB → actual routing)
- NSAI shadow → active mode (actually route based on NSAI recommendation)
- Runner health monitoring dashboard
- Cost optimization based on MAB learned preferences
- Paper evaluation notebook consuming BigQuery data
