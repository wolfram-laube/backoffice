# HANDOVER: AppTrack Sprint 2 — Crawl Integration

**Datum:** 2026-02-09
**Session:** Sprint 2 Crawl Integration + GCS Setup
**Author:** Wolfram Laube + Claude

---

## ✅ GCS Setup (Task 1)

| Step | Status |
|------|--------|
| GCS Bucket `blauweiss-apptrack` created | ✓ (europe-west3, STANDARD) |
| CSV → SQLite import (187 apps) | ✓ |
| DB upload to GCS (172 KB) | ✓ |
| Export verified (download → JSON + CSV) | ✓ |
| Fixed stale `GCP_SA_KEY` CI variable | ✓ (updated from group-level key) |

### GCS Details
- **Bucket:** `gs://blauweiss-apptrack`
- **Location:** EUROPE-WEST3 (Frankfurt)
- **Lifecycle:** Delete non-current versions after 30 days
- **SA:** `gitlab-runner-controller@myk8sproject-207017.iam.gserviceaccount.com`

### Note on SA Keys
- Project-level `GCP_SA_KEY` was stale (key ID `f3f115a1...`) → updated with working key
- Group-level `GCP_SERVICE_ACCOUNT_KEY` is base64-encoded → `database.py` expects raw JSON via `GCP_SA_KEY`
- Both variables now use key ID `2d328d70...`

---

## ✅ Sprint 2 — Crawl Integration (on MR !19)

### Commits (2 on `feature/53-apptrack-sprint2-crawl`)

| Commit | Description |
|--------|-------------|
| `874251ad` | crawl_service.py, 3 CI scripts, tests, __init__.py (6 files) |
| `8e4baec2` | CI config: 4 new AppTrack jobs in applications.yml |

### GitLab Artifacts

| Item | Link |
|------|------|
| Issue #53 | `ops/backoffice/-/issues/53` |
| MR !19 | https://gitlab.com/wolfram_laube/blauweiss_llc/ops/backoffice/-/merge_requests/19 |
| Branch | `feature/53-apptrack-sprint2-crawl` |

### Files Created/Modified

```
modules/applications/
├── __init__.py           ← MODIFIED (Sprint 2 exports)
└── crawl_service.py      ← NEW: Core crawl integration logic

scripts/ci/
├── apptrack_ingest_crawl.py     ← NEW: crawl output → crawl_results
├── apptrack_update_matches.py   ← NEW: match scores → crawl_results
└── apptrack_stage_approved.py   ← NEW: approved → Applications + CRM

tests/unit/
└── test_crawl_service.py        ← NEW: 32 tests

.gitlab/applications.yml          ← MODIFIED: +4 CI jobs
```

### Test Results

```
32 passed in 0.57s

TestExtractExternalId    (5) — URL parsing, edge cases
TestNormalizeSource      (4) — Source normalization
TestIngestCrawlResults   (6) — Insert, dedup, skip, raw_data
TestIngestFromFile       (1) — File loading
TestUpdateMatchScores    (4) — Score updates, status promotion
TestStageToApplication   (4) — Staging, idempotency, AI flag
TestGetCrmLabel          (7) — Status → label mapping
TestFullPipelineFlow     (1) — End-to-end: crawl → ingest → match → stage
```

Sprint 1 tests also verified: **30 passed** (no regressions)

### Pipeline Architecture

```
applications:crawl (existing)
  → output/projects.json
    → apptrack:ingest-crawl (NEW)        ─── GCS-managed SQLite ───
      → crawl_results table                                        │
                                                                   │
applications:match (existing)                                      │
  → output/matches.json                                            │
    → apptrack:update-matches (NEW)                                │
      → match_score on crawl_results     ←─────────────────────────┘
        → status promoted to "matched" (if score ≥ 70)

apptrack:stage-approved (NEW)
  → Application records from approved crawl_results
  → CRM sync: GitLab Issue labels from Application status
```

### CI Jobs Added

| Job | Stage | Triggers | Description |
|-----|-------|----------|-------------|
| `apptrack:ingest-crawl` | build | After crawl, `APPTRACK_INGEST=true` | Write projects to DB |
| `apptrack:update-matches` | test | After ingest + match, `APPTRACK_MATCH=true` | Update scores |
| `apptrack:stage-approved` | deploy | After update-matches, `APPTRACK_STAGE=true` | Create apps + CRM |
| `apptrack:test` | test | Changes to apptrack files, `APPLICATIONS_TEST=true` | 32 tests |

All jobs run automatically when `APPLICATIONS_PIPELINE=true` (schedule) or manually.

### Key Design Decisions

1. **Idempotent operations** — Re-running any step is safe (dedup by source/external_id)
2. **Status flow** — `new` → `matched` (score ≥ 70) → `applied` (staged as Application)
3. **CRM sync** — Bidirectional: Application status → GitLab Issue labels
4. **Separate from existing pipeline** — New `apptrack:*` jobs DON'T break existing `applications:*` jobs

---

## 🔲 Next Steps

### To Merge MR !19
- [ ] Review MR !19 and merge to main
- [ ] Trigger `applications:test` + `apptrack:test` on main to verify

### Sprint 2 Remaining (manual verification)
- [ ] Trigger full pipeline: crawl → ingest → match → update → stage
- [ ] Verify CRM Issue creation in project #78171527
- [ ] Test with real crawl data (not just test fixtures)

### Sprint 3: Pages Frontend
- [ ] GitLab Pages HTML dashboard (read dashboard.json)
- [ ] Pipeline trigger button on Pages
- [ ] Status filter, search, sorting
- [ ] Statistics charts

### Backlog
- [ ] Issue #50: CI failure on main (ci-regression-confirmed)
- [ ] Issue #26: NSAI JKU Bachelor Paper Draft
- [ ] Issue #29: GitHub Mirroring EPIC
- [ ] NSAI Paper: Quarto-Projekt committen

---

## 🔑 Credentials (Reference)

- GitLab PAT: `glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj`
- User: wolfram.laube (ID: 1349601)
- GCP SA: `gitlab-runner-controller@myk8sproject-207017.iam.gserviceaccount.com`
- GCS Bucket: `blauweiss-apptrack` (europe-west3)
- Backoffice: 77555895
- Corporate: 77075415
- CRM: 78171527
