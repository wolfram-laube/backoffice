# 🎯 Operations

Operative Tools und Prozesse für Blauweiss EDV.

## Übersicht

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        OPERATIONS STACK                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│  │   APPLICATIONS  │    │      CRM        │    │    BILLING      │     │
│  │    Pipeline     │───▶│  (GitLab Issues)│    │   (Timesheets)  │     │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘     │
│          │                      │                      │               │
│          ▼                      ▼                      ▼               │
│    Gmail Drafts           Kanban Board           Google Drive          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Module

### 📊 CRM — Bewerbungs-Tracking

GitLab Issues-basiertes CRM für Freelance-Bewerbungen.

- **185 Issues** mit Status-Tracking
- **Kanban Board** mit 8-Spalten-Pipeline
- **Automatische QA** (weekly)
- **Label-System** für Rate, Tech, Branche

👉 [CRM Dokumentation](crm.md)

### 🚀 Applications Pipeline

Automatisierte Job-Suche und Bewerbungs-Erstellung.

- **Crawl** → freelancermap.de Scanner
- **Match** → Profil-basiertes Scoring
- **QA** → Validierung + CRM-Dedup
- **Drafts** → Gmail-Entwürfe

👉 [Applications Pipeline Dokumentation](applications-pipeline.md)

### 💰 Billing (Coming Soon)

Automatisierte Zeiterfassung und Rechnungsstellung.

- Timesheet-Generierung
- Google Drive Sync
- PDF-Erstellung

## Schedules

| Schedule | Cron | Beschreibung |
|----------|------|--------------|
| Applications Pipeline | `0 8 * * 1-5` | Mo-Fr 08:00 (vorbereitet) |
| CRM Integrity Check | `0 7 * * 1` | Mo 07:00 |
| Monthly Billing | `0 6 1 * *` | 1. des Monats 06:00 |

## Quick Links

| Resource | Link |
|----------|------|
| CRM Board | [Kanban](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/boards/10081703) |
| CRM Issues | [Issues](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/issues) |
| Pipelines | [CLARISSA Pipelines](https://gitlab.com/wolfram_laube/blauweiss_llc/projects/clarissa/-/pipelines) |
| Schedules | [Pipeline Schedules](https://gitlab.com/wolfram_laube/blauweiss_llc/projects/clarissa/-/pipeline_schedules) |

## Architektur

Die Operations-Tools sind Teil des **Blauweiss LLC GitLab-Monorepos**:

```
blauweiss_llc/
├── ops/
│   ├── crm/           # CRM Projekt (Issues)
│   ├── billing/       # Billing Projekt
│   └── backoffice/    # Backoffice Projekt
├── projects/
│   └── clarissa/      # CLARISSA (CI/CD, Scripts)
└── (group-level labels)
```

Siehe [ADR-018: GitLab PM Workflow](../architecture/adr/ADR-018-gitlab-pm-workflow.md) für Details.
