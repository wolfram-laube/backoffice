# CLARISSA Billing System - Handover für neuen Chat

## 🎯 Aktueller Stand

Das Billing-System ist **funktionsfähig und automatisiert**.

### Was funktioniert ✅
- Zeit tracken via GitLab `/spend` Command
- **`spent_at` Datum wird korrekt erfasst** (via GraphQL API) ✨
- Timesheets generieren (pro Consultant)
- Konsolidierte Rechnung aus mehreren Timesheets
- CI/CD Pipeline: `.typ` → PDF → Google Drive Upload
- Google Drive Shared Drive Integration (BLAUWEISS-EDV-LLC)
- Negative Zeiteinträge (Korrekturen) werden korrekt verarbeitet
- **Automatische monatliche Timesheet-Generierung** (Scheduled Pipeline) ✨

### Was noch offen ist 🔧
- Template-Validierung (Typst compile check vor Upload)
- Approval-Workflow mit Flag in .sync.json (P3)

---

## 📁 Relevante Dateien im Repo

```
gitlab.com/wolfram_laube/blauweiss_llc/clarissa (Project ID: 77260390)

billing/
├── config/
│   ├── clients.yaml          # Kunden, Stundensätze, Consultants, gitlab_label
│   └── sequences.yaml        # Rechnungsnummern-Zähler
├── scripts/
│   ├── generate_timesheet.py # ✅ Nutzt GraphQL API für korrekte Datums
│   ├── generate_invoice.py   # Liest .sync.json, konsolidiert, erstellt Rechnung
│   └── upload_to_drive.py    # Google Drive Upload mit Shared Drive Support
├── templates/
│   ├── timesheet.typ         # Typst Template mit Unterschriftsfeldern
│   ├── rechnung-de.typ       # Deutsche Rechnung
│   ├── invoice-en-us.typ     # US Invoice
│   └── invoice-en-eu.typ     # EU Invoice (Reverse Charge)
└── output/
    ├── *.typ                 # Generierte Dokumente
    ├── *.sync.json           # Metadaten für Invoice-Generator
    └── *.pdf                 # (nur in CI Artifacts)

.gitlab-ci.yml                # Jobs: generate_timesheets, build_invoice, upload_invoice
```

---

## 🤖 Automatisierung

### Scheduled Pipeline
- **Wann:** 1. des Monats um 06:00 Wiener Zeit
- **Was:** Generiert Timesheets für alle Clients/Consultants für den Vormonat
- **Schedule ID:** 4094512
- **Variable:** `BILLING_RUN=true`

### Manueller Trigger
Pipeline manuell starten mit Variables:
- `GENERATE_TIMESHEETS=true` - Timesheets generieren
- `BILLING_PERIOD=2026-01` - Optional: Spezifische Periode (sonst Vormonat)

---

## ✅ GELÖST: Time Entry Parsing

### Die Lösung: GraphQL API
Die GraphQL API gibt `spentAt` korrekt zurück (im Gegensatz zur REST Notes API):
```graphql
query {
  project(fullPath: "wolfram_laube/blauweiss_llc/clarissa") {
    issues(labelName: ["client:nemensis"]) {
      nodes {
        timelogs {
          nodes {
            spentAt      # ← Korrektes Datum!
            timeSpent
            user { username }
          }
        }
      }
    }
  }
}
```

---

## 🔧 clients.yaml Struktur

```yaml
consultants:
  wolfram:
    name: "Wolfram Laube"
    gitlab_username: "wolfram.laube"
  ian:
    name: "Ian Matejka"
    gitlab_username: "ian.matejka"

clients:
  nemensis:
    name: "nemensis AG Deutschland"
    gitlab_label: "client:nemensis"
    rates:
      remote: 105
      onsite: 120
    consultants:
      - wolfram
      - ian
    approver:
      name: "Max Mustermann"
      title: "Projektleiter"
```

---

## 🔄 Workflow

```
1. User arbeitet an Issue mit Label "client:nemensis"
2. User: /spend 4h 2026-01-15   ← Datum wird korrekt erfasst
3. Am 1. des Folgemonats: Scheduled Pipeline läuft automatisch
   → Generiert Timesheets für alle Consultants
4. Timesheets werden geprüft & unterschrieben
5. generate_invoice.py --client nemensis --period 2026-01
   → Erstellt konsolidierte Rechnung
6. git push → CI → PDFs → Google Drive
```

---

## 🔑 Credentials

```
GitLab Project: 77260390
GitLab PAT: glpat-B2kbE0n56oTpioepn5ZT-W86MQp1OnN4Y3gK.01.1007svpwt

Google Drive Folder: 1qh0skTeyRNs4g9KwAhpd3J8Yj_XENIFs
Service Account: claude-assistant@myk8sproject-207017.iam.gserviceaccount.com

Scheduled Pipeline: 4094512
```

---

## 📋 Test-Kommandos

```bash
# Timesheet generieren (lokal)
export GITLAB_TOKEN="glpat-xxx"
export GITLAB_PROJECT_PATH="wolfram_laube/blauweiss_llc/clarissa"
python billing/scripts/generate_timesheet.py --client nemensis --period 2026-01 --all-consultants

# Rechnung generieren
python billing/scripts/generate_invoice.py --client nemensis --period 2026-01

# Scheduled Pipeline manuell triggern
curl -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/77260390/pipeline_schedules/4094512/play"

# Pipeline mit Variables triggern
curl -X POST -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ref":"main","variables":[{"key":"GENERATE_TIMESHEETS","value":"true"},{"key":"BILLING_PERIOD","value":"2026-01"}]}' \
  "https://gitlab.com/api/v4/projects/77260390/pipeline"
```

---

## 🧪 Test-Issues

- Issue #36: NLP Pipeline Development - `client:nemensis` Label
- Issue #37: Docker Integration - `client:nemensis` Label
