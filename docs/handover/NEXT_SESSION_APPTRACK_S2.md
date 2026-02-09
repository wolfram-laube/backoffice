# Next Session: AppTrack — GCS Setup + Sprint 2

## Kontext

Sprint 1 ist auf `main` gemerged (MR !18, Commit `1de29312`). EPIC #52 erstellt, alle EPICs im Repo konsistent.

Lies bitte: `docs/handover/HANDOVER_APPTRACK_SPRINT1_DONE_09_02_2026.md` im backoffice Repo.

## Aufgaben

### 1. GCS Setup + Initial Seed (~10 min)
- GCS Bucket `blauweiss-apptrack` erstellen (oder Subfolder in bestehendem Bucket)
- `applications:import-csv` Job manuell triggern → SQLite auf GCS seeden
- `applications:export` triggern → end-to-end verifizieren (dashboard.json + CSV)

### 2. Sprint 2: Crawl Integration (ADR-004)
- Wire crawl pipeline output → `crawl_results` Tabelle
- Match pipeline → `match_score` auf crawl_results updaten
- Stage pipeline → Application aus approved CrawlResult erstellen
- CRM sync → Issue Labels aus Application Status

### Offene Punkte (Backlog)
- Issue #50: CI failure auf main (ci-regression-confirmed)
- Issue #26: NSAI JKU Bachelor Paper Draft
- Issue #29: GitHub Mirroring EPIC
- NSAI Paper: Quarto-Projekt committen

## Credentials
- GitLab PAT: `glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj`
- User: wolfram.laube (ID: 1349601)
- GCP SA: `claude-assistant@myk8sproject-207017.iam.gserviceaccount.com`
- Backoffice: 77555895
- Corporate: 77075415
- CRM: 78171527
