# NEXT SESSION: AppTrack Sprint 3 — Finalize + Deploy

**Datum:** 2026-02-09
**Kontext:** Sprint 3 Files sind erstellt, müssen committed + deployed werden

---

## Was ist passiert

Sprint 2 ist komplett (MR !19, Pipeline verifiziert, Issue #50 gefixt).
Sprint 3 Dashboard (`apptrack-dashboard.html`) + Tests (`test_dashboard_data.py`) + Handover sind erstellt und auf Branch `feature/55-apptrack-sprint3-pages` committed.

## Was zu tun ist

### 1. Sprint 3 finalisieren
Auf Branch `feature/55-apptrack-sprint3-pages`:

- [ ] `mkdocs.yml` updaten — Nav-Entry hinzufügen:
  ```yaml
  # Unter "🎯 Operations" oder als eigene Sektion:
  - "📊 AppTrack": apptrack-dashboard.html
  ```

- [ ] `.gitlab/applications.yml` updaten — Dashboard-Test-Job hinzufügen:
  ```yaml
  apptrack:dashboard-test:
    extends: .applications-base
    needs: []
    stage: test
    rules:
      - changes:
          - docs/apptrack-dashboard.html
          - tests/unit/test_dashboard_data.py
          - scripts/ci/applications_export_json.py
      - when: manual
        allow_failure: true
    before_script:
      - pip install sqlalchemy pytest --quiet
    script:
      - python3 -m pytest tests/unit/test_dashboard_data.py -v --tb=short
  ```

- [ ] Tests lokal verifizieren: `pytest tests/unit/test_dashboard_data.py -v`
- [ ] MR erstellen → Review → Merge
- [ ] `applications:export` triggern (generiert `dashboard.json`)
- [ ] Dashboard auf Pages verifizieren: https://bewerbung-tool-372f49.gitlab.io/apptrack-dashboard.html

### 2. Issue #55 schließen + Epic #52 Sprint 3 ✅ markieren

### 3. Optional: Sprint 4 planen
- Nightly CSV export → Git commit
- Status change notifications
- Duplicate detection

---

## Referenzen

| Item | Location |
|------|----------|
| Epic #52 | `ops/backoffice/-/issues/52` |
| Issue #55 | `ops/backoffice/-/issues/55` |
| Branch | `feature/55-apptrack-sprint3-pages` |
| Dashboard | `docs/apptrack-dashboard.html` |
| Tests | `tests/unit/test_dashboard_data.py` |
| Handover | `docs/handover/HANDOVER_APPTRACK_SPRINT3_09_02_2026.md` |
| Pages | https://bewerbung-tool-372f49.gitlab.io/ |
| Backoffice Project | 77555895 |
| CRM Project | 78171527 |
| GCS Bucket | `blauweiss-apptrack` (europe-west3) |
