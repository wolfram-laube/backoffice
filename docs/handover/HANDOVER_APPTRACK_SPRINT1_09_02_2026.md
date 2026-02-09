# HANDOVER: Application Tracking System – ADR-004 & Sprint 1

**Datum:** 2026-02-09
**Session:** Bewerbungsrunde + ADR-004 Architektur-Entscheidung
**Author:** Wolfram Laube + Claude

---

## 🎯 Was wurde erreicht

### 1. Bewerbungsrunde (6 Bewerbungen)

| # | Projekt | Provider | Match | Status |
|---|---------|----------|-------|--------|
| 190 | Databricks AI/ML Engineer – Wien 3 Jahre | Qualysoft (Elena Kahraman) | 55-60% | versendet (Email mit Remote-Hinweis) |
| 191 | Software Engineer Backend Python/Django – Berlin (POS70017) | CAES GmbH via Randstad/GULP | 75-80% | versendet via GULP |
| 192 | Solution Architect KI-Plattform – Bahn/Logistik (2965789) | freelance.de | 85% | versendet via freelance.de |
| 193 | Solution Architekt KI – Frankfurt/Remote | teamative (Harcenko/Günther) | 85% | versendet per Email |
| 194 | DevOps/Platform Engineer – Berlin (POS70013) | CAES GmbH via Randstad/GULP | 95%+ | versendet via GULP |

Abgelehnt/Übersprungen:
- Servicedesign & IT-Dokumentation (Karlsruhe) – Junior, Best-Price, unter Niveau
- Fullstack Developer Kotlin/React (Frankfurt) – Kotlin 5y + React 3y = K.O.-Kriterien

### 2. CSV aktualisiert

`bewerbungen_komplett_SORTED_Jan_31_2026.csv` hat jetzt 5 neue Einträge (Zeilen 189-194).
Die CSV liegt im Projekt-Ordner (read-only in Claude) und muss noch ins Git-Repo committed werden.

### 3. ADR-004: Application Tracking System

**Architektur-Entscheidung nach 3 Iterationen:**

| Iteration | Ansatz | Verworfen weil |
|-----------|--------|----------------|
| 1 | FastAPI + Cloud Run + GCS | Neue Infrastruktur, GCS-Abhängigkeit |
| 2 | FastAPI auf Nordic VM + SQLite lokal | VM ist preemptible, muss 24/7 laufen |
| 3 ✅ | **CI-Triggered Pipeline + SQLite/GCS + Pages** | Keine neue Infrastruktur nötig |

**Kernentscheidung:** Kein permanenter Server. GitLab Pages Button triggert CI Pipeline.
CI-Job lädt SQLite von GCS, arbeitet, exportiert JSON für Frontend, lädt DB zurück.
Nightly CSV-Export ins Git als Fallback.

**ADR als HTML:** `ADR-004-application-tracking-system.html` – im ADR-027 Dark-Theme-Design
mit Dialektik, Architektur-Diagramm, Workflow-Pipeline, Datenmodell, Sprint-Roadmap.

---

## 📁 Erstellte Dateien (im Claude-Output)

| Datei | Beschreibung |
|-------|-------------|
| `databricks_response_qualysoft.txt` | Email an Elena Kahraman (mit Remote-Hinweis) |
| `bewerbung_caes_gulp_1500.txt` | GULP-Text Django Backend POS70017 (1180 Zeichen) |
| `bewerbung_caes_devops_pos70013.txt` | GULP-Text DevOps POS70013 (1343 Zeichen) |
| `bewerbung_teamative_ki_architect.txt` | Email an teamative KI Solution Architect |
| `ADR-004-application-tracking-system.html` | ADR im Dark-Theme (schmuck) |
| `ADR-004-application-tracking-system.md` | ADR als Markdown (veraltet – HTML ist aktuell) |

---

## 🏗️ Sprint 1: Foundation – Aufgaben

### 1. ADR-004 committen (corporate)

```
ops/corporate/docs/adr/ADR-004-application-tracking-system.html
```
Commit-Message: `docs(adr): ADR-004 application tracking system (CI-triggered pipeline)`

### 2. SQLAlchemy Models definieren

```python
# backoffice/modules/applications/models.py
# Drei Tabellen: applications, crawl_results, application_history
# SQLAlchemy 2.0 Style mit Mapped Columns
```

Felder siehe ADR-004 Datenmodell.

### 3. Alembic Migration Setup

```
backoffice/modules/applications/
├── models.py
├── database.py      # Engine, Session, GCS up/download
├── migrations/
│   ├── env.py
│   └── versions/
│       └── 001_initial.py
└── __init__.py
```

### 4. CSV → SQLite Import Script

```python
# backoffice/scripts/ci/applications_import_csv.py
# Liest bewerbungen_komplett_SORTED_Jan_31_2026.csv
# Erstellt applications.db mit allen 190+ Einträgen
# Parst: match_score aus notes (z.B. "MATCH 85%!" → 85)
```

### 5. GCS State Management

```python
# backoffice/modules/applications/database.py
# download_db(bucket, blob) → lokale Datei
# upload_db(lokale Datei, bucket, blob)
# Pattern: exakt wie runner_bandit GCS State
```

GCS Bucket: `blauweiss-apptrack` (neu anlegen) oder bestehenden Bucket nutzen.

### 6. JSON-Export für Pages

```python
# backoffice/scripts/ci/applications_export_json.py
# DB → dashboard.json (für Pages-Frontend)
# DB → CSV (für Git-Fallback)
```

### 7. CI-Job in applications.yml

```yaml
# .gitlab/applications.yml
applications:export:
  stage: deploy
  script:
    - pip install sqlalchemy google-cloud-storage
    - python scripts/ci/applications_export_json.py
  artifacts:
    paths:
      - public/dashboard.json
  rules:
    - if: $APPLICATIONS_EXPORT == "true"
```

---

## 🔧 Bestehende Infrastruktur (Referenz)

### Runner-Landschaft

| Runner ID | Name | Location | Status |
|-----------|------|----------|--------|
| 51336735 | Mac Docker Runner | Lokal | ✅ online |
| 51337424 | Mac2 Docker Runner | Lokal | ✅ online |
| 51337426 | Linux Yoga Docker Runner | Lokal | ✅ online |
| 51608579 | gitlab-runner-nordic | GCP Stockholm | ✅ online |

### Bestehende CI Schedules

| Schedule | Cron | Variable |
|----------|------|----------|
| #4126476 Monthly Billing | `0 6 1 * *` | `BILLING_RUN=true` |
| #4126477 CRM Integrity | `0 7 * * 1` | `CRM_INTEGRITY_CHECK=true` |
| #4126478 Applications | `0 8 * * 1-5` | `APPLICATIONS_PIPELINE=true` |

### Repo-Struktur

```
ops/backoffice/                    ← ALL OPERATIONS
├── .gitlab/
│   ├── billing.yml
│   ├── applications.yml           ← HIER: neue Jobs
│   └── ...
├── modules/
│   ├── billing/                   ← Existiert
│   └── applications/              ← NEU: Sprint 1
│       ├── models.py
│       ├── database.py
│       └── migrations/
├── scripts/ci/
│   ├── applications_crawl.py      ← Existiert
│   ├── applications_import_csv.py ← NEU
│   └── applications_export_json.py ← NEU
└── tests/
    └── unit/
        └── test_applications_*.py ← NEU
```

### GCP

- VM: `gitlab-runner-nordic` (europe-north2-a, e2-small, preemptible)
- Service Account: `claude-assistant@myk8sproject-207017.iam.gserviceaccount.com`
- MAB Service: `https://runner-bandit-m5cziijwqa-lz.a.run.app/`
- GCS: Neuen Bucket `blauweiss-apptrack` anlegen (oder Subfolder in bestehendem)

---

## 🔑 Credentials

- **GitLab PAT:** `glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj`
- **User:** wolfram.laube (ID: 1349601)
- **GitHub PAT:** `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`
- **GCP SA:** `claude-assistant@myk8sproject-207017.iam.gserviceaccount.com`
- **Project-Level CI Var:** `GCP_SA_KEY` (für Drive/Gmail/GCS)
- **Group-Level CI Vars:** `GCP_SERVICE_ACCOUNT_KEY`, `GMAIL_*` tokens

### Repos

- ops/backoffice: **77555895**
- ops/crm: **78171527**
- ops/corporate: **77075415**
- projects/clarissa: **77260390**

---

## ⚠️ Offene Punkte (aus vorherigen Sessions)

- [ ] NSAI Paper: Quarto-Projekt committen (backoffice) – HANDOVER_QUARTO_PIPELINE_07_02_2026.md
- [ ] GOV-003 committen (corporate)
- [ ] Issue #379 CRM Data Quality
- [ ] Issue #26 Status-Update
- [ ] Pipeline #495 Cloud Run Deploy
- [ ] GitHub Mirror Refactoring (#29)

---

## 📊 Aktuelle Bewerbungs-Highlights (Hot Leads)

| Projekt | Status | Nächster Schritt |
|---------|--------|-----------------|
| Hoffmann Werkzeuge (DevOps/Databricks) | Profil "sehr spannend" | Interview-Feedback abwarten |
| Wien MLOps/Platform Engineer | 4 Agenturen | Grafton stellt beim Kunden vor |
| KONSENS/GPU Stuttgart | 5 Agenturen | Feedback abwarten |
| Databricks 3 Jahre (Qualysoft) | Email versendet | Antwort abwarten |
| KI-Plattform Bahn (freelance.de + teamative) | 2x beworben | Feedback abwarten |
