# NEXT SESSION: Application Tracking System – Sprint 1 Foundation

## Prompt

```
Kontext: ADR-004 ist entschieden. Application Tracking System wird von CSV 
auf SQLite/GCS migriert mit CI-Triggered Pipeline und GitLab Pages Frontend.
Kein permanenter Server. Heute: Sprint 1 Foundation.

Lies zuerst das Handover:
- /mnt/project/HANDOVER_APPTRACK_SPRINT1_09_02_2026.md
- /mnt/project/ADR-004-application-tracking-system.html (Architektur-Referenz)

Die aktuelle CSV mit 190+ Bewerbungen liegt unter:
- /mnt/project/bewerbungen_komplett_SORTED_Jan_31_2026.csv

Sprint 1 Aufgaben:
1. ADR-004 HTML ins corporate Repo committen
2. SQLAlchemy Models (applications, crawl_results, application_history)
3. Alembic Migration Setup
4. CSV → SQLite Import Script (190+ Einträge, match_score aus Notes parsen)
5. GCS State Management (download/upload wie MAB-Service)
6. JSON-Export Script für Pages-Frontend
7. CI-Job applications:export in .gitlab/applications.yml
8. Tests für Models + Import + Export

Paradigma: Issue → Branch → Code → Tests → Docs → MR
Bitte alle Fehler sofort fixen, nicht für später aufheben.

Credentials:
- GitLab PAT: glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj
- User: wolfram.laube (ID: 1349601)
- GCP SA: claude-assistant@myk8sproject-207017.iam.gserviceaccount.com
- Backoffice Project ID: 77555895
- Corporate Project ID: 77075415

Repos:
- ops/backoffice (77555895) - Operations, neue Module hier
- ops/corporate (77075415) - ADRs
- ops/crm (78171527) - CRM Issues

Bestehende Referenz-Implementierung:
- services/runner_bandit/ im backoffice Repo (GCS State Pattern)
- services/nsai/ im backoffice Repo (SQLAlchemy-ähnliche Patterns)

MAB Service (als Referenz für GCS Pattern):
- https://runner-bandit-m5cziijwqa-lz.a.run.app/
```
