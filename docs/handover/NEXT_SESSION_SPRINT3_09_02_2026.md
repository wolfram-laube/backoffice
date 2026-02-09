# NEXT SESSION PROMPT — AppTrack Sprint 3

Lies zuerst das Handover:
* `docs/handover/HANDOVER_APPTRACK_SPRINT3_09_02_2026.md`

## Kontext

Sprint 2 abgeschlossen: Full Pipeline verifiziert (crawl→ingest→match→update→stage), test:unit gefixt (229 passed), GitHub bidirektionaler Sync für alle 3 Repos eingerichtet, Issue #50/#54 geschlossen, EPIC #29 geschlossen. Milestones angelegt.

## Sprint 3 Scope

**Milestone:** AppTrack Sprint 3 — Pages Frontend (id: 7297434, due: 2026-02-15)
**Issue:** #55 — [Sprint 3] Pages Frontend — AppTrack Dashboard on GitLab Pages
**EPIC:** #52

### Deliverables
1. HTML Dashboard das `dashboard.json` liest (aus `applications:export` Job)
2. Pipeline Trigger Button auf Pages
3. Status Filter, Search, Sorting
4. Statistics Charts (Funnel, Timeline, Source Breakdown)

### Existing Infrastructure
- `pages` Job deployt `public/` → https://wolfram_laube.gitlab.io/blauweiss_llc/ops/backoffice/
- `applications:export` generiert `public/dashboard.json`
- DB: 187 Applications + Crawl Results in GCS SQLite

## Credentials
* GitLab PAT: `glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj`
* GitHub PAT: `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`
* User: wolfram.laube (ID: 1349601)
* Repos: backoffice=77555895, corporate=77075415, CRM=78171527

## Open Issues (5)
| # | Title |
|---|-------|
| #52 | EPIC AppTrack (Sprint 3) |
| #55 | Sprint 3 Pages Frontend |
| #49 | JOB-MATCH 97% Cloud Architect |
| #48 | Vorhölle Service |
| #27 | EPIC Neurosymbolic AI |
| #26 | NSAI Paper Draft |

