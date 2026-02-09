# HANDOVER: AppTrack Sprint 4 — Vorhölle Review Layer

**Datum:** 2026-02-09
**Session:** Sprint 4 Implementation
**Author:** Wolfram Laube + Claude
**MR:** !21 — `feature/48-apptrack-sprint4-vorhoelle → main`

---

## 🎯 Sprint 4 Scope

**Goal:** Introduce a "Vorhölle" (Purgatory) review layer between automated matching and application creation.

**Problem solved:** Previously, `stage_all_approved()` auto-promoted all CrawlResults with `score >= 70` directly to Applications. No human review step existed.

**Solution:** New `pending_review` status with explicit approve/dismiss workflow.

---

## ✅ Deliverables

| Deliverable | File | Status |
|---|---|---|
| Review Service | `modules/applications/review_service.py` | ✅ |
| Tests (28 cases) | `tests/unit/test_review_service.py` | ✅ |
| CI Promotion Script | `scripts/ci/apptrack_promote_review.py` | ✅ |
| CI Job | `.gitlab/applications.yml` → `apptrack:promote-review` | ✅ |
| Dashboard Tab | `docs/apptrack-dashboard.html` → Vorhölle tab | ✅ |
| Module Exports | `modules/applications/__init__.py` | ✅ |

---

## 📐 Architecture

### Updated Status Flow

```
CrawlResult (new)
  → matched (score assigned by match pipeline)
    → pending_review (score >= threshold)     ← NEW
      → applied (manually approved → Application created)
      → dismissed (with reason, audit trail)  ← NEW
```

### Pipeline Flow (Updated)

```
applications:crawl → projects.json
  → apptrack:ingest-crawl → crawl_results (GCS SQLite)
    → applications:match → matches.json
      → apptrack:update-matches → match_score on crawl_results
        → apptrack:promote-review → pending_review status    ← NEW
          → (manual review via Dashboard)
            → apptrack:stage-approved → Applications + CRM Issues
```

### Review Service API

```python
from modules.applications.review_service import (
    promote_to_review,      # matched → pending_review (min_score filter)
    approve_crawl_result,   # pending_review → applied (creates Application)
    dismiss_crawl_result,   # pending_review → dismissed (with reason)
    get_review_queue,       # list pending_review items (sorted)
    approve_all_above,      # bulk approve above threshold
    get_review_summary,     # statistics for dashboard
)
```

---

## 🧪 Test Coverage

**28 test cases** in `test_review_service.py`:

| Test Class | Cases | Coverage |
|---|---|---|
| TestPromoteToReview | 8 | threshold, skip, idempotent, None score, exact threshold |
| TestApprove | 5 | creates app, wrong status, not found, dismissed, field mapping |
| TestDismiss | 5 | with/without reason, wrong status, not found, preserves reasons |
| TestReviewQueue | 5 | empty, filter, sort desc/asc, field completeness |
| TestBulkOperations | 2 | approve_all_above, review_summary |
| TestCrawlStatuses | 2 | status constants validation |

---

## 🔑 CI Jobs

### New: `apptrack:promote-review`
- **Stage:** test
- **Needs:** `apptrack:update-matches`
- **Trigger:** schedule, web/api with `$APPTRACK_REVIEW=true`, or manual
- **Output:** `output/apptrack_review_queue.json`

### Updated: `apptrack:stage-approved`
- **Needs:** `apptrack:promote-review` (optional)
- Now only processes manually approved items from review queue

### Updated: `apptrack:test`
- Now includes `test_review_service.py` in test suite

---

## 📊 Dashboard Changes

New **Vorhölle tab** in `docs/apptrack-dashboard.html`:
- Tab bar: Bewerbungen | 🔥 Vorhölle (with pending count badge)
- Review queue cards with match score, keywords, AI tag
- Approve / Dismiss buttons per card
- Summary bar: pending, applied, dismissed, score range
- Animated card removal on action
