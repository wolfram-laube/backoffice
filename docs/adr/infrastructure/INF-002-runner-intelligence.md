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
| `.gitlab/mab-integration.yml` | v2: passive pipeline-level reporting, remove unused template |
| `.gitlab/ci-automation.yml` | `gcp-shell` → `shell-any` |
| `.gitlab/k3s-setup.yml` | `gcp-shell` → `nordic` |
| `.gitlab/fix-shell-runner.yml` | `gcp-docker` → `nordic` |
| `.gitlab/ci-metrics.yml` | Fix git checkout conflict in dashboard job |
| `services/nsai/ontology/runner_ontology.py` | 4 → 11 runners, add IDs, K8s + Shell |
| Nordic runner tags | Added `shell-any`, `any-runner`, `gcp-any` |
| Runner registration | All 11 runners → all 5 projects |

## Consequences

### Positive

- MAB starts learning from real pipeline data immediately (passive, no job changes)
- Fallback actually works (uses tags that exist)
- NSAI ontology reflects reality (11 runners, not 4)
- All projects can use all runners (balanced load)
- Clean separation: availability ≠ selection ≠ reasoning

### Negative / Trade-offs

- `mab:report` adds ~15s to every pipeline (`.post` stage)
- MAB service needs to handle 11 runners (was 4) — UCB1 scales fine
- NSAI tests may need updating for new runner count
- Nordic K8s Runner still offline (k3s not running)

### Future Work

- Dynamic runner selection via child pipelines (MAB → actual routing)
- NSAI CSP integration in `.pre` stage (filter infeasible runners)
- Runner health monitoring dashboard
- Cost optimization based on MAB learned preferences
