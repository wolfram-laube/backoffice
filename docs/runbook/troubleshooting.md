# Troubleshooting Runbook

> Wenn's brennt - schnelle Hilfe.

---

## 🚨 Quick Diagnostics

```bash
# Welche Pipelines sind gerade kaputt?
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/77555895/pipelines?status=failed&per_page=5" | \
  jq '.[] | {id, ref, status, created_at}'

# Runner-Status
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/77555895/runners" | \
  jq '.[] | {id, description, status, active}'
```

---

## Pipeline-Probleme

### ❌ "Pipeline stuck in pending"

**Symptom:** Job bleibt ewig in "pending", startet nie.

**Ursachen:**
1. Kein Runner verfügbar
2. Runner-Tag stimmt nicht
3. Runner ist offline

**Diagnose:**
```bash
# Runner-Status prüfen
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/77555895/runners" | jq
```

**Fix:**
- GCP Runner starten: Trigger `runner-fallback.yml`
- Oder: macOS Runner aufwecken (nur wenn Lid offen)

---

### ❌ "Job failed: exit code 1"

**Symptom:** Job läuft, bricht aber mit Fehler ab.

**Diagnose:**
1. Job-Log lesen (letzte 50 Zeilen)
2. Nach Python Traceback suchen
3. Nach "Error:" oder "Exception:" suchen

**Häufige Ursachen:**

| Error | Ursache | Fix |
|-------|---------|-----|
| `ModuleNotFoundError` | Package fehlt | `pip install X` in CI |
| `FileNotFoundError` | Pfad falsch | Pfade prüfen |
| `PermissionDenied` | Token/Credentials | CI vars prüfen |
| `JSONDecodeError` | API Response kaputt | Retry oder API prüfen |

---

### ❌ "Runner offline"

**Symptom:** Alle Jobs pending, Runner zeigt "offline".

**GCP Runner (gcp-runner-stockholm):**
```bash
# Status prüfen
gcloud compute instances describe gcp-runner-stockholm \
  --zone=europe-north1-a --format="value(status)"

# Starten
gcloud compute instances start gcp-runner-stockholm \
  --zone=europe-north1-a
```

**macOS Runner:**
- MacBook aufklappen
- Oder: Wake-on-LAN senden (wenn konfiguriert)

---

## Credential-Probleme

### ❌ "401 Unauthorized" / "403 Forbidden"

**Symptom:** API-Calls schlagen fehl.

**GitLab Token:**
```bash
# Token testen
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/user" | jq .username
```

**Fix:**
1. Token auf GitLab erneuern: Settings → Access Tokens
2. CI Variable aktualisieren: Settings → CI/CD → Variables
3. Variable: `GITLAB_TOKEN`

---

### ❌ "Google API: invalid_grant"

**Symptom:** Google Drive/Gmail Calls schlagen fehl.

**Ursache:** OAuth Refresh Token abgelaufen (nach 7 Tagen ohne Nutzung).

**Fix:**
```bash
# Lokal neu authentifizieren
python scripts/auth/google_oauth.py --refresh

# Neues Token in CI Variable hochladen
# Variable: GOOGLE_CREDENTIALS (Base64 encoded)
```

---

### ❌ "Service account has no access"

**Symptom:** Google Drive Upload scheitert.

**Ursache:** Service Account nicht zum Shared Drive eingeladen.

**Fix:**
1. Google Drive → BLAUWEISS-EDV-LLC
2. Rechtsklick → Share
3. Service Account Email hinzufügen: `claude-assistant@myk8sproject-207017.iam.gserviceaccount.com`

---

## CRM-Probleme

### ❌ "Issue not visible on board"

**Symptom:** Issue existiert, aber nicht im Board.

**Ursache:** Fehlendes oder falsches Status-Label.

**Fix:**
```bash
# Labels des Issues prüfen
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/78171527/issues/42" | jq .labels

# Status-Label hinzufügen
curl -X PUT -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  -d "labels=status::neu" \
  "https://gitlab.com/api/v4/projects/78171527/issues/42"
```

---

### ❌ "CRM Integrity Check failed"

**Symptom:** Weekly Check meldet Fehler.

**Diagnose:** Pipeline-Log lesen, zeigt welche Issues betroffen.

**Häufige Probleme:**

| Problem | Bedeutung | Fix |
|---------|-----------|-----|
| `Missing status` | Issue ohne Status-Label | Label hinzufügen |
| `Multiple status` | >1 Status-Label | Eines entfernen |
| `Ghost detected` | 30+ Tage keine Aktivität | Follow-up oder Ghost-Label |
| `Orphan label` | Label ohne Issues | Label löschen |

---

## Billing-Probleme

### ❌ "No time entries found"

**Symptom:** Timesheet ist leer.

**Diagnose:**
```bash
# Time entries via GraphQL prüfen
curl -s -H "Authorization: Bearer $GITLAB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"{ project(fullPath:\"wolfram_laube/blauweiss_llc/projects/clarissa\") { issues(labelName:[\"client:nemensis\"]) { nodes { title timelogs { nodes { spentAt timeSpent } } } } } }"}' \
  "https://gitlab.com/api/graphql" | jq
```

**Häufige Ursachen:**

| Ursache | Fix |
|---------|-----|
| Falsches Client-Label | Label auf Issues prüfen |
| Falsche Periode | `BILLING_PERIOD` Variable prüfen |
| `/spend` ohne Datum | Datum muss explizit angegeben werden |

---

### ❌ "Typst compilation failed"

**Symptom:** .typ existiert, aber kein PDF.

**Diagnose:**
```bash
# Lokal testen
typst compile billing/output/test.typ

# Fehler zeigt Zeile und Problem
```

**Häufige Ursachen:**
- Fehlende Fonts → `fonts/` Ordner prüfen
- Ungültige UTF-8 Zeichen → Encoding prüfen
- Template-Syntax-Fehler → Typst-Doku konsultieren

---

## Gmail-Probleme

### ❌ "Draft not created"

**Symptom:** Pipeline läuft durch, aber keine Drafts in Gmail.

**Diagnose:**
```bash
# Prüfen ob Drafts existieren
python -c "
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
# ... auth code ...
service = build('gmail', 'v1', credentials=creds)
drafts = service.users().drafts().list(userId='me').execute()
print(drafts)
"
```

**Häufige Ursachen:**
- OAuth Token abgelaufen
- `DRAFTS_JSON_B64` Variable leer/falsch
- Gmail API Quota exceeded

---

## Allgemeine Tipps

### Log-Analyse

```bash
# Letzte 100 Zeilen eines Jobs
curl -s -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/77555895/jobs/123456/trace" | tail -100
```

### Retry mit sauberem Cache

```bash
# Pipeline mit frischem Cache
curl -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  -d '{"ref":"main","variables":[{"key":"CLEAR_CACHE","value":"true"}]}' \
  "https://gitlab.com/api/v4/projects/77555895/pipeline"
```

### Notfall: Manuell ausführen

Wenn CI komplett kaputt:

```bash
# Lokal klonen und ausführen
git clone git@gitlab.com:wolfram_laube/blauweiss_llc/ops/backoffice.git
cd backoffice
pip install -r requirements.txt
python scripts/ci/billing_generate.py --period 2026-01
```

---

## Kontakte

| Problem | Wer | Wie |
|---------|-----|-----|
| GitLab Runner | Wolfram | `wolfram.laube@blauweiss-edv.at` |
| GCP | Wolfram | GCP Console |
| Google Workspace | Wolfram | Admin Console |
| Code-Fragen | Claude | Dieser Chat 😉 |

---

## Änderungshistorie

| Datum | Änderung | Autor |
|-------|----------|-------|
| 2026-02-04 | Initial version | Wolfram + Claude |
