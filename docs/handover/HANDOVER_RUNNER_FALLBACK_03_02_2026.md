# Handover: Runner-Fallback-System & CLARISSA Final Cleanup

**Datum:** 03.02.2026  
**Session:** Weiter Wurf - Komplett-Migration + Runner-Fallback

---

## Executive Summary

CLARISSA ist jetzt ein **reines Research-Repository**. Alle Ops- und Infra-Komponenten wurden nach `ops/backoffice` migriert. Ein neues **Runner-Fallback-System** ermöglicht automatische Runner-Auswahl mit GCP-Auto-Start.

---

## 1. CLARISSA Cleanup (abgeschlossen)

### Vorher
CLARISSA war ein "God Class" Repository mit:
- Research Code (Reservoir-Simulation)
- Ops (Portal, CRM, Applications)
- Infra (GCP, Terraform, Docker, K3s)
- CI/CD für alles

### Nachher
**CLARISSA (.gitlab/):**
- `clarissa.yml` - Research CI
- `conference/` - Paper builds
- **Das ist alles!**

**backoffice (.gitlab/):**
```
applications.yml      # Bewerbungs-Pipeline
benchmark.yml         # Performance Tests
billing.yml           # Rechnungen
ci-automation.yml     # CRM Bots
docker-build.yml      # Container
fix-shell-runner.yml  # Runner Fixes
gcp-check.yml         # GCP Status
gcp-setup.yml         # GCP Setup
gdrive-upload.yml     # Drive Sync
gmail-drafts.yml      # Email Drafts (mit Attachments!)
infra-setup.yml       # Infra
k3s-setup.yml         # Kubernetes
pages.yml             # Portal
parallel-jobs.yml     # Job-Parallelisierung
roundtrip-test.yml    # Integration Tests
runner-fallback.yml   # NEU: Smart Runner Selection
terraform.yml         # IaC
```

---

## 2. Runner-Fallback-System

### Architektur

```
Pipeline getriggert (Schedule, API, Web, Trigger)
            ↓
┌─────────────────────────────────────────────┐
│  .pre: runner-check                         │
│                                             │
│  1. Check: local-shell Runner online?       │
│     → mac#1, mac#2, yoga                    │
│                                             │
│  2. Check: gcp-shell Runner online?         │
│     → Nordic Shell Runner                   │
│                                             │
│  3. Falls beide offline:                    │
│     → GCP VM automatisch starten            │
│     → Warten bis Runner online              │
│                                             │
│  Output: RUNNER_TAG, RUNNER_SOURCE          │
└─────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────┐
│  Nachfolgende Jobs                          │
│  tags: ["${RUNNER_TAG}"]                    │
│  → Laufen auf verfügbarem Runner            │
└─────────────────────────────────────────────┘
            ↓
┌─────────────────────────────────────────────┐
│  .post: gcp-auto-stop (optional)            │
│  Falls GCP_AUTO_STOP=true und               │
│  RUNNER_SOURCE=gcp-started                  │
│  → VM wieder abschalten                     │
└─────────────────────────────────────────────┘
```

### Verfügbare Runner

| Runner | Tags | Status |
|--------|------|--------|
| Nordic Shell Runner | shell, gcp, gcp-shell, any-runner | 🟢 online |
| Nordic Docker Runner | docker, gcp, gcp-docker, any-runner | 🟢 online |
| mac#1, mac#2, yoga | local-shell | 🔴 nicht registriert |

### Manuelle Kontrolle

Jobs im Pipeline-UI:
- `gcp-vm-start` - VM manuell starten
- `gcp-vm-stop` - VM manuell stoppen
- `gcp-vm-status` - VM Status prüfen
- `runner-status` - Alle Runner anzeigen

---

## 3. Credentials (Group-Level)

Alle auf `blauweiss_llc` Group (120698013):

| Variable | Zweck | Masked |
|----------|-------|--------|
| GMAIL_CLIENT_ID | Gmail API | ✅ |
| GMAIL_CLIENT_SECRET | Gmail API | ✅ |
| GMAIL_REFRESH_TOKEN | Gmail API | ✅ |
| GITLAB_API_TOKEN | Runner-Check | ✅ |
| GCP_SERVICE_ACCOUNT_KEY | GCP Auth (base64) | ❌ |

---

## 4. Gmail-Drafts mit Attachments

Die `gmail-drafts.yml` unterstützt jetzt Attachments:

```json
[
  {
    "to": "email@example.com",
    "subject": "Bewerbung",
    "body": "Text...",
    "attachments": ["attachments/Profil_Laube_w_Summary_DE.pdf"]
  }
]
```

Trigger via API oder Pipeline Variable `DRAFTS_JSON_B64`.

---

## 5. Offene Punkte

### TODO: Lokale Runner registrieren

Auf mac#1, mac#2, yoga:
```bash
gitlab-runner register \
  --url https://gitlab.com \
  --registration-token <TOKEN> \
  --description "Mac Mini #1" \
  --tag-list "local-shell,mac,shell" \
  --executor shell \
  --locked=false
```

### TODO: gcp-vm-control.yml löschen
Ist obsolet (in runner-fallback.yml integriert), aber noch als Datei vorhanden.

### Optional: GCP_AUTO_STOP aktivieren
Für Pipelines die GCP starten: `GCP_AUTO_STOP=true` setzen um Kosten zu sparen.

---

## 6. Wichtige URLs

| Resource | URL |
|----------|-----|
| backoffice | https://gitlab.com/wolfram_laube/blauweiss_llc/ops/backoffice |
| CLARISSA | https://gitlab.com/wolfram_laube/blauweiss_llc/projects/clarissa |
| CRM | https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm |
| Portal (neu) | https://wolfram_laube.gitlab.io/blauweiss_llc/ops/backoffice/ |
| Tech-Backlog | https://gitlab.com/wolfram_laube/blauweiss_llc/ops/backoffice/-/boards/10083330 |

---

## 7. Test-Pipeline

Pipeline #2303096816 läuft (runner-check wartet auf GitLab SaaS Runner):
https://gitlab.com/wolfram_laube/blauweiss_llc/ops/backoffice/-/pipelines/2303096816

---

*Erstellt: 03.02.2026 ~14:15 UTC*
