# HANDOVER: AppTrack Sprint 3 — Pages Frontend Dashboard

**Datum:** 2026-02-09
**Session:** Sprint 2 Completion + Sprint 3 Dashboard
**Author:** Wolfram Laube + Claude

---

## ✅ Session Summary

### Sprint 2 Wrap-Up (completed this session)

| Task | Status |
|------|--------|
| MR !19 reviewed + merged | ✓ (already merged at session start) |
| `test:unit` on main verified | ✓ (229 passed after fix) |
| Issue #50 fixed (`sqlalchemy` missing in requirements.txt) | ✓ (commit `c17ab7f5`) |
| `pyyaml` added to `.applications-base` | ✓ (commit `5e1e0b31`) |
| Full pipeline: crawl → ingest → match → update → stage | ✓ (Pipeline #553) |
| CRM Issues verified (#411–#415 with labels) | ✓ |
| Issue #50 closed with root cause comment | ✓ |

### Sprint 3: Pages Frontend Dashboard

| Task | Status |
|------|--------|
| Issue #55 created | ✓ |
| Epic #52 updated (Sprint 2 ✅, Sprint 3 linked) | ✓ |
| Feature branch `feature/55-apptrack-sprint3-pages` | ✓ |
| `docs/apptrack-dashboard.html` created | ✓ |
| `tests/unit/test_dashboard_data.py` created | ✓ |
| `mkdocs.yml` nav entry | 🔲 (needs commit) |
| `.gitlab/applications.yml` test job update | 🔲 (needs commit) |
| Commit + MR | 🔲 |
| Pipeline verification | 🔲 |

---

## 📁 Files Created/Modified

### New Files

```
docs/apptrack-dashboard.html           ← Main dashboard page
tests/unit/test_dashboard_data.py      ← 22 tests (schema, stats, status, integration)
docs/handover/HANDOVER_APPTRACK_SPRINT3_09_02_2026.md  ← This file
```

### Files to Modify (next commit)

```
mkdocs.yml                             ← Add nav entry for dashboard
.gitlab/applications.yml               ← Add apptrack:dashboard-test job
```

---

## 🎯 Dashboard Features

### `docs/apptrack-dashboard.html`

- **Stats Cards:** Total, Versendet, In Kontakt, Abgelehnt, Ø Rate, Ø Match Score
- **Interactive Table:** Sortable columns, pagination (25/page), source links
- **Search & Filter:** Full-text search, status dropdown, month dropdown
- **Charts (Chart.js):**
  - Status distribution (doughnut)
  - Monthly trend (bar)
  - Top providers (horizontal bar)
  - Rate histogram (bar, 10€ buckets)
- **Pipeline Trigger:** Modal with PAT input, triggers `APPLICATIONS_PIPELINE=true`
- **Design:** Dark theme matching existing portal (same CSS variables)
- **Data Source:** Fetches `dashboard.json` at runtime (relative path)

### `tests/unit/test_dashboard_data.py` — 22 Tests

```
TestDashboardJsonSchema     (3)  — Required keys, field presence, statistics structure
TestStatisticsComputation   (7)  — Empty, count, rate avg/min/max, monthly, providers, match
TestStatusClassification    (7)  — versendet, abgelehnt, in_kontakt, verhandlung, etc.
TestDashboardIntegration    (4)  — DB seed → export, crawl summary, date serialization
```

---

## 🔧 Technical Details

### Dashboard Data Flow

```
applications:export (CI job)
  → downloads DB from GCS
  → runs export_json()
  → outputs public/dashboard.json
  → deployed via pages job to GitLab Pages

apptrack-dashboard.html (browser)
  → fetch('dashboard.json')
  → render stats, charts, table
  → pipeline trigger via GitLab API
```

### Pages URL
- Portal: https://bewerbung-tool-372f49.gitlab.io/
- Dashboard: https://bewerbung-tool-372f49.gitlab.io/apptrack-dashboard.html

### GitLab Artifacts

| Item | Link |
|------|------|
| Epic #52 | `ops/backoffice/-/issues/52` |
| Issue #55 | `ops/backoffice/-/issues/55` |
| Branch | `feature/55-apptrack-sprint3-pages` |

---

## 🔲 Next Steps (to complete Sprint 3)

### Immediate (next session)
- [ ] Commit files to `feature/55-apptrack-sprint3-pages`
- [ ] Update `mkdocs.yml` with nav entry: `"📊 AppTrack": apptrack-dashboard.html`
- [ ] Update `.gitlab/applications.yml` with `apptrack:dashboard-test` job
- [ ] Run tests locally/CI (22 tests)
- [ ] Create MR !20 (or next available)
- [ ] Review + merge
- [ ] Trigger `applications:export` to generate `dashboard.json`
- [ ] Verify dashboard on GitLab Pages

### Optional Enhancements
- [ ] CSV download button on dashboard
- [ ] Detail view modal (click row → full application details)
- [ ] Auto-refresh (poll dashboard.json every 5 min)
- [ ] Dark/light theme toggle
- [ ] Export filtered results

---

## 🔑 Credentials (Reference)

- GitLab PAT: `glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj`
- User: wolfram.laube (ID: 1349601)
- GCP SA: `gitlab-runner-controller@myk8sproject-207017.iam.gserviceaccount.com`
- GCS Bucket: `blauweiss-apptrack` (europe-west3)
- Backoffice: 77555895
- Corporate: 77075415
- CRM: 78171527
- Pages URL: https://bewerbung-tool-372f49.gitlab.io/
