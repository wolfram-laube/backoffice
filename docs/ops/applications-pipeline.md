# 🚀 Applications Pipeline

Automatisierte Job-Suche und Bewerbungs-Erstellung für Freelance-Projekte.

## Übersicht

```
┌──────────────────────────────────────────────────────────────────────┐
│                    APPLICATIONS PIPELINE                              │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐           │
│  │  CRAWL  │───▶│  MATCH  │───▶│   QA    │───▶│ DRAFTS  │           │
│  │  .pre   │    │  build  │    │  test   │    │ deploy  │           │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘           │
│       │              │              │              │                 │
│       ▼              ▼              ▼              ▼                 │
│  projects.json  matches.json  qa_report.json  Gmail Drafts          │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Manuell triggern

```bash
# Volle Pipeline
curl -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/77260390/pipeline" \
  -d '{"ref":"main","variables":[{"key":"APPLICATIONS_CRAWL","value":"true"}]}'

# Einzelne Stage
# APPLICATIONS_CRAWL=true  → nur Crawl
# APPLICATIONS_MATCH=true  → nur Match
# APPLICATIONS_QA=true     → nur QA
# APPLICATIONS_DRAFTS=true → nur Drafts
```

### Schedule (Automatisch)

Die Pipeline ist für tägliche Ausführung vorbereitet:

```yaml
Cron: 0 8 * * 1-5  # Mo-Fr 08:00
Variable: APPLICATIONS_PIPELINE=true
```

## Pipeline-Stages

### Stage 1: Crawl

**Job:** `applications:crawl`  
**Stage:** `.pre`  
**Output:** `output/projects.json`

Crawlt freelancermap.de nach Projekten mit konfigurierbaren Keywords.

```yaml
variables:
  KEYWORDS: "DevOps Kubernetes,Python Cloud,AI ML LLM,Java Spring Architekt,MLOps Platform"
  MIN_REMOTE: "50"      # Minimum Remote-Anteil
  MAX_PAGES: "3"        # Seiten pro Keyword
  FETCH_DETAILS: "true" # Projekt-Beschreibungen laden
```

**Output-Schema:**
```json
{
  "id": "projekt-12345",
  "title": "Senior DevOps Engineer (m/w/d)",
  "url": "https://freelancermap.de/...",
  "location": "Remote / Frankfurt",
  "remote_pct": 80,
  "rate": "105",
  "start_date": "01.03.2026",
  "duration": "12 Monate",
  "description": "..."
}
```

### Stage 2: Match

**Job:** `applications:match`  
**Stage:** `build`  
**Input:** `output/projects.json`  
**Output:** `output/matches.json`

Bewertet Projekte gegen vordefinierte Profile.

**Profile:**

| Profil | Fokus | Keywords |
|--------|-------|----------|
| `wolfram` | DevOps/Cloud/AI | kubernetes, python, aws, azure, ai, ml |
| `ian` | AI/ML Engineering | python, ml, ai, llm, pytorch, tensorflow |
| `michael` | Project Management | agile, scrum, pm, lead, coordination |
| `team` | Kombination Wolfram+Ian | combined keywords |

**Scoring:**
```python
must_have:    weight 3  # Pflicht-Keywords
strong_match: weight 2  # Starke Übereinstimmung
nice_to_have: weight 1  # Bonus-Keywords
exclude:      weight 0  # Ausschluss (instant 0%)
```

**AI-Bonus:** Projekte mit AI/ML/LLM Keywords bekommen +1000 Punkte im Ranking.

### Stage 3: QA

**Job:** `applications:qa`  
**Stage:** `test`  
**Input:** `projects.json`, `matches.json`  
**Output:** `output/qa_report.json`

Validiert die Pipeline-Outputs.

**Checks:**

| Check | Beschreibung | Threshold |
|-------|--------------|-----------|
| `file_exists` | Dateien vorhanden | required |
| `json_valid` | Gültiges JSON | required |
| `crawl.volume` | Anzahl Projekte | 5-500 |
| `schema.required` | Pflichtfelder | id, title, url |
| `duplicates.internal` | Keine doppelten URLs | 0 |
| `match.rate` | Match-Quote pro Profil | 10-95% |
| `crm.dedup` | Nicht schon im CRM | info |

**Exit Codes:**
```
0 = PASS  → Pipeline weiter
1 = FAIL  → Pipeline stoppt
2 = WARN  → Pipeline weiter (mit Hinweis)
```

### Stage 4: Drafts

**Job:** `applications:drafts`  
**Stage:** `deploy`  
**Input:** `output/matches.json`  
**Output:** Gmail Drafts

Erstellt Gmail-Entwürfe für die Top-Matches.

```yaml
variables:
  MAX_DRAFTS: "5"       # Anzahl Drafts
  DRAFT_PROFILE: "wolfram"  # Profil für E-Mail-Template
```

**E-Mail-Template:**

- **AI-Projekte:** Betont AI-Bachelor JKU + ML-Erfahrung
- **DevOps-Projekte:** Betont CKA/CKAD + Kubernetes-Expertise
- **Energie-Projekte:** Betont 50Hertz KRITIS-Erfahrung

**Benötigte CI-Variablen:**
```yaml
GMAIL_CLIENT_ID: "..."      # OAuth Client ID
GMAIL_CLIENT_SECRET: "..."  # OAuth Client Secret
GMAIL_REFRESH_TOKEN: "..."  # OAuth Refresh Token
```

## Configuration

### Pipeline-Variablen

| Variable | Default | Beschreibung |
|----------|---------|--------------|
| `KEYWORDS` | DevOps,Python,AI... | Komma-separierte Suchbegriffe |
| `MIN_REMOTE` | 50 | Minimum Remote % |
| `MAX_PAGES` | 3 | Seiten pro Keyword |
| `MIN_SCORE` | 50 | Minimum Match-Score % |
| `MAX_RESULTS` | 20 | Top-N Matches pro Profil |
| `MAX_DRAFTS` | 5 | Anzahl Gmail-Drafts |
| `DRAFT_PROFILE` | wolfram | Profil für Drafts |

### Profile anpassen

Profile sind definiert in:
```
src/admin/applications/pipeline/profiles.py
```

```python
WOLFRAM = Profile(
    name="wolfram",
    must_have=["kubernetes", "python", "devops"],
    strong_match=["aws", "azure", "terraform", "ai"],
    nice_to_have=["kafka", "grafana", "prometheus"],
    exclude=["sap", "cobol", "mainframe"]
)
```

## Artifacts

Alle Outputs werden als Artifacts gespeichert:

| Artifact | Retention | Beschreibung |
|----------|-----------|--------------|
| `output/projects.json` | 7 Tage | Gecrawlte Projekte |
| `output/matches.json` | 7 Tage | Match-Ergebnisse |
| `output/qa_report.json` | 7 Tage | QA-Report (JUnit) |

## Runner-Konfiguration

Die Pipeline läuft auf Docker-Runnern:

```yaml
.applications-base:
  image: python:3.11-slim
  tags:
    - docker-any
  before_script:
    - pip install requests beautifulsoup4 lxml --quiet
```

**Verfügbare Runner:**

- `Linux Yoga Docker Runner` (docker-any) — primary
- `Mac2 Docker Runner` (docker-any) — fallback

## Monitoring

### Pipeline-Status

[Pipeline Dashboard](https://gitlab.com/wolfram_laube/blauweiss_llc/projects/clarissa/-/pipelines?scope=all&page=1&ref=main)

### Letzte Runs

```bash
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://gitlab.com/api/v4/projects/77260390/pipelines?per_page=5" | \
  jq '.[] | {id, status, created_at}'
```

### Job-Logs

```bash
# Crawl-Log
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://gitlab.com/api/v4/projects/77260390/jobs/{JOB_ID}/trace"
```

## Troubleshooting

### Crawl findet keine Projekte

1. Keywords zu spezifisch? → Erweitern
2. freelancermap blockiert? → Rate limiting, später versuchen
3. Seiten-Struktur geändert? → Scraper prüfen

### Match-Score zu niedrig

1. Profile-Keywords anpassen
2. `MIN_SCORE` reduzieren (default: 50)
3. Exclude-Liste prüfen

### Gmail Drafts werden nicht erstellt

1. OAuth Tokens gültig? → Refresh Token erneuern
2. CI-Variablen gesetzt? → `GMAIL_*` prüfen
3. Quota erschöpft? → Gmail API Limits

### QA schlägt fehl

```bash
# Lokaler Test
cd /path/to/clarissa
export GITLAB_TOKEN="..."
python3 scripts/ci/applications_qa.py --crm-dedup
```

## Integration

### CRM-Integration

Die QA-Stage prüft gegen das CRM:

```python
# --crm-dedup Flag
# Vergleicht Match-Titel mit existierenden Issues
# Markiert bereits beworbene Projekte
```

### Notifications

Bei Pipeline-Fehlern werden E-Mail-Benachrichtigungen gesendet (GitLab-Standard).

## Scripts

| Script | Pfad | Beschreibung |
|--------|------|--------------|
| Crawl | `scripts/ci/applications_crawl.py` | freelancermap Scraper |
| Match | `scripts/ci/applications_match.py` | Profile Matching |
| QA | `scripts/ci/applications_qa.py` | Validierung |
| Drafts | `scripts/ci/applications_drafts.py` | Gmail Draft Creator |
| Profiles | `src/admin/applications/pipeline/profiles.py` | Profil-Definitionen |

## Changelog

| Datum | Änderung |
|-------|----------|
| 2026-02-02 | Migration von mac-group-shell zu docker-any |
| 2026-02-02 | QA-Stage mit CRM-Dedup hinzugefügt |
| 2026-01-28 | Initiale Pipeline-Implementierung |
