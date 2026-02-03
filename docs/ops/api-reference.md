# 🔗 API Reference

GitLab API Integration und Pipeline-Trigger für das Blauweiss Operations Portal.

## Authentifizierung

### Pipeline Trigger Token

Für automatisierte Pipeline-Starts ohne persönlichen Token:

```
Token ID: #4821279
Token: glptt-4o... (masked)
Scope: Pipeline triggers
```

**Verwendung:**
```bash
curl -X POST \
  -F "token=TRIGGER_TOKEN" \
  -F "ref=main" \
  -F "variables[VAR_NAME]=value" \
  "https://gitlab.com/api/v4/projects/77260390/trigger/pipeline"
```

### Personal Access Token

Für API-Operationen die mehr Rechte benötigen:

```
Scope: api (read/write)
Expires: 2026-12-31
```

**Verwendung:**
```bash
curl -H "PRIVATE-TOKEN: glpat-..." \
  "https://gitlab.com/api/v4/projects/77260390/..."
```

## Pipeline Trigger Variablen

### Applications Pipeline

| Variable | Wert | Beschreibung |
|----------|------|--------------|
| `APPLICATIONS_PIPELINE` | `true` | Volle Pipeline (crawl→match→qa→drafts) |
| `APPLICATIONS_CRAWL` | `true` | Nur Crawl |
| `APPLICATIONS_MATCH` | `true` | Nur Match |
| `APPLICATIONS_QA` | `true` | Nur QA |
| `APPLICATIONS_DRAFTS` | `true` | Nur Drafts |

**Crawl-Optionen:**
```bash
variables[KEYWORDS]="DevOps,Python,AI"
variables[MIN_REMOTE]="50"
variables[MAX_PAGES]="3"
```

**Match-Optionen:**
```bash
variables[MIN_SCORE]="50"
variables[MAX_RESULTS]="20"
variables[DRAFT_PROFILE]="wolfram"
```

### CRM Pipeline

| Variable | Wert | Beschreibung |
|----------|------|--------------|
| `CRM_QA` | `true` | CRM Integrity Check |
| `CRM_INTEGRITY_CHECK` | `true` | (Alias für Schedule) |

### Billing Pipeline

| Variable | Wert | Beschreibung |
|----------|------|--------------|
| `BILLING_PIPELINE` | `true` | Timesheet + Invoice |
| `BILLING_MONTH` | `2026-01` | Spezifischer Monat |

### Infrastructure

| Variable | Wert | Beschreibung |
|----------|------|--------------|
| `START_LINUX_RUNNER` | `true` | Linux Runner starten |
| `STOP_LINUX_RUNNER` | `true` | Linux Runner stoppen |
| `CHECK_LINUX_STATUS` | `true` | Linux Status prüfen |
| `START_MAC2_RUNNER` | `true` | Mac Runner starten |
| `GCP_VM_START` | `true` | GCP VM starten |
| `GCP_VM_STOP` | `true` | GCP VM stoppen |

## API Endpoints

### GitLab Project API

**Base URL:** `https://gitlab.com/api/v4`

| Endpoint | Method | Beschreibung |
|----------|--------|--------------|
| `/projects/77260390/pipelines` | GET | Liste Pipelines |
| `/projects/77260390/pipelines` | POST | Neue Pipeline |
| `/projects/77260390/jobs/{id}/trace` | GET | Job-Logs |
| `/projects/78171527/issues` | GET | CRM Issues |
| `/projects/78171527/issues` | POST | Neues CRM Issue |

### CRM Project API

**Project ID:** `78171527`

**Issues abrufen:**
```bash
curl -H "PRIVATE-TOKEN: $TOKEN" \
  "https://gitlab.com/api/v4/projects/78171527/issues?labels=hot-lead"
```

**Issue erstellen:**
```bash
curl -X POST -H "PRIVATE-TOKEN: $TOKEN" \
  -d "title=[Agentur] Position" \
  -d "labels=status::versendet,rate::105+" \
  "https://gitlab.com/api/v4/projects/78171527/issues"
```

**Issue updaten:**
```bash
curl -X PUT -H "PRIVATE-TOKEN: $TOKEN" \
  -d "add_labels=hot-lead" \
  "https://gitlab.com/api/v4/projects/78171527/issues/{iid}"
```

## Webhooks

### Pipeline Events

GitLab kann bei Pipeline-Events Webhooks senden:

1. GitLab → Settings → Webhooks
2. URL: `https://your-endpoint.com/webhook`
3. Trigger: Pipeline events
4. Secret Token: (optional)

**Payload-Beispiel:**
```json
{
  "object_kind": "pipeline",
  "object_attributes": {
    "id": 123456,
    "status": "success",
    "stages": ["build", "test", "deploy"]
  }
}
```

## Code-Beispiele

### Python: Pipeline triggern

```python
import requests

GITLAB_API = "https://gitlab.com/api/v4"
PROJECT_ID = "77260390"
TRIGGER_TOKEN = "glptt-..."

def trigger_pipeline(variables: dict):
    response = requests.post(
        f"{GITLAB_API}/projects/{PROJECT_ID}/trigger/pipeline",
        data={
            "token": TRIGGER_TOKEN,
            "ref": "main",
            **{f"variables[{k}]": v for k, v in variables.items()}
        }
    )
    return response.json()

# Beispiel: Applications Pipeline
result = trigger_pipeline({"APPLICATIONS_PIPELINE": "true"})
print(f"Pipeline #{result['id']}: {result['web_url']}")
```

### JavaScript: CRM Issues abrufen

```javascript
const GITLAB_API = 'https://gitlab.com/api/v4';
const CRM_PROJECT = '78171527';
const TOKEN = 'glpat-...';

async function getHotLeads() {
    const response = await fetch(
        `${GITLAB_API}/projects/${CRM_PROJECT}/issues?labels=hot-lead`,
        { headers: { 'PRIVATE-TOKEN': TOKEN } }
    );
    return response.json();
}

// Beispiel
const hotLeads = await getHotLeads();
console.log(`${hotLeads.length} Hot Leads gefunden`);
```

### Bash: CRM Integrity Check

```bash
#!/bin/bash
export GITLAB_TOKEN="glpat-..."
export CRM_PROJECT_ID="78171527"

# Alle Issues abrufen
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/$CRM_PROJECT_ID/issues?per_page=100" | \
  jq '.[] | {iid, title, labels}'
```

## Rate Limits

GitLab API hat folgende Limits:

| Authentifizierung | Limit |
|-------------------|-------|
| Unauthentifiziert | 60/Stunde |
| Personal Token | 2000/Minute |
| Pipeline Trigger | Kein explizites Limit |

**Best Practices:**

- Batch-Requests wenn möglich
- Caching für häufige Abfragen
- Pagination für große Ergebnismengen (`per_page=100&page=N`)

## Projekt-IDs

| Projekt | ID | Pfad |
|---------|----|----- |
| CLARISSA | 77260390 | wolfram_laube/blauweiss_llc/projects/clarissa |
| CRM | 78171527 | wolfram_laube/blauweiss_llc/ops/crm |
| Billing | 78171234 | wolfram_laube/blauweiss_llc/ops/billing |
| Group (LLC) | 120698013 | wolfram_laube/blauweiss_llc |

## Troubleshooting

### 401 Unauthorized

- Token abgelaufen → Neuen Token erstellen
- Falscher Token-Typ → Trigger Token vs. PAT prüfen

### 403 Forbidden

- Keine Berechtigung für Projekt
- Token hat falschen Scope

### 429 Too Many Requests

- Rate Limit erreicht → Warten oder Requests reduzieren

### Pipeline startet nicht

- Ref (Branch) existiert nicht
- Variable-Name falsch geschrieben
- Job-Rules matchen nicht
