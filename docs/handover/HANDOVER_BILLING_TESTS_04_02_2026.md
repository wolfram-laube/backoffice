# HANDOVER: Billing Migration & Test Suite
**Datum:** 2026-02-04
**Session:** OPS-001 Billing Migration Testing & Runner Cleanup

---

## 🎯 Was wurde erreicht

### 1. Test Suite für Billing Module
- **55 Unit Tests** erstellt und passing
- Location: `ops/backoffice/tests/`
  - `fixtures/billing.py` - Test fixtures
  - `unit/test_billing_timesheet.py` - 19 Tests
  - `unit/test_billing_invoice.py` - 22 Tests
  - `unit/test_billing_integration.py` - 14 Tests
- Commit: `26427529`

### 2. Schedule Migration CLARISSA → Backoffice
Alle operativen Schedules jetzt in backoffice:

| Schedule | Cron | Variable | Status |
|----------|------|----------|--------|
| #4126476 Monthly Billing | `0 6 1 * *` | `BILLING_RUN=true` | ✅ Active |
| #4126477 CRM Integrity | `0 7 * * 1` | `CRM_INTEGRITY_CHECK=true` | ✅ Active |
| #4126478 Applications | `0 8 * * 1-5` | `APPLICATIONS_PIPELINE=true` | ✅ Active |

CLARISSA Schedules (#4094512, #4125129, #4125172) sind deaktiviert.

### 3. CI/CD Fixes
- **Pipeline Source Rules**: `api` trigger zusätzlich zu `web` und `schedule` akzeptiert
- **Runner Tags**: `shell` und `docker-any` korrekt konfiguriert
- Commits: `07c362d0`, `d2e2d0a5`

### 4. Runner Cleanup
**Gelöscht (5 tote Runner):**
- 51602770: ops-docker-runner (Duplikat)
- 51396165: Nordic Docker Runner (offline)
- 51396166: Nordic Shell Runner (offline)
- 51602505: gitlab-runner-nordic (never_contacted)
- 51602688: ops-shell-runner (offline)

**Verbleibend:**
| Runner ID | Name | Location | Status |
|-----------|------|----------|--------|
| 51336735 | Mac Docker Runner | Lokal | ✅ online |
| 51337424 | Mac2 Docker Runner | Lokal | ✅ online |
| 51337426 | Linux Yoga Docker Runner | Lokal | ✅ online |
| 51608579 | gitlab-runner-nordic | GCP Stockholm | ✅ online |

### 5. Final Test Results
```
generate_timesheets   ✅ success    15.5s   gitlab-runner-nordic
crm:integrity-check   ❌ failed*    17.7s   gitlab-runner-nordic
applications:crawl    ✅ success   166.6s   gitlab-runner-nordic

* CRM failed correctly - found Issue #379 without status label
```

---

## 📁 Aktuelle Architektur

```
ops/backoffice/                    ← ALL OPERATIONS
├── .gitlab/
│   ├── billing.yml               ✅ Migrated, tags: shell
│   ├── applications.yml          ✅ API trigger added
│   └── ...
├── modules/billing/              ✅ From CLARISSA
├── scripts/ci/
│   ├── crm_integrity_check.py
│   ├── applications_*.py
│   └── billing scripts
├── tests/
│   ├── fixtures/billing.py       ✅ NEW
│   └── unit/test_billing_*.py    ✅ 55 tests
└── docs/runbook/index.md         ✅ Updated

projects/clarissa/                 ← RESEARCH ONLY
└── All schedules deactivated
```

---

## 🔧 GCP Infrastructure

**VM:** `gitlab-runner-nordic`
- Zone: europe-north2-a (Stockholm)
- Type: e2-small (preemptible)
- IP: 34.51.185.83
- Services: gitlab-runner, docker, k3s

**Service Account:** `gitlab-runner-controller@myk8sproject-207017.iam.gserviceaccount.com`

---

## ⚠️ Bekannte Issues

1. **CRM Data Quality:**
   - Issue #379 hat kein Status-Label
   - 18 unbekannte Labels im CRM

2. **CI Minutes:**
   - Shared Runner CI Minutes waren erschöpft
   - Gelöst durch Nutzung eigener Runner (gitlab-runner-nordic)

---

## 📋 Offene Punkte / Nächste Schritte

- [ ] Issue #379 im CRM fixen (Status-Label hinzufügen)
- [ ] Unbekannte CRM Labels bereinigen oder definieren
- [ ] CLARISSA billing/ Ordner löschen (nach Bewährungszeit)
- [ ] Smoke Test der scheduled Runs abwarten (nächster Montag)
- [ ] ADR-002 für Testing-Strategie schreiben
- [ ] **EPIC: GitHub Mirroring Refactoring**
  - Zweck: Jupyter Notebooks & Google Colab Integration
  - Aktuell: Nur CLARISSA gespiegelt (historisch gewachsen)
  - Prüfen: Welche Repos brauchen Mirror für Notebook-Zugriff?
  - Ggf. backoffice oder andere Repos hinzufügen

---

## 🔑 Credentials (Reference)

**Direkt:**
- **GitLab PAT:** `glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj` (User: wolfram.laube, ID: 1349601)
- **Google Service Account:** `claude-assistant@myk8sproject-207017.iam.gserviceaccount.com`

**GitLab CI Variables - Project (backoffice / 77555895):**
- `GCP_SA_KEY` - Google Service Account für Drive/Gmail
- `GITLAB_TOKEN` - API Token
- `GITLAB_API_TOKEN` - API Token

**GitLab CI Variables - Group (blauweiss_llc / 120698013):**
- `GCP_SERVICE_ACCOUNT_KEY` - Runner Controller für VM Start/Stop
- `GMAIL_CLIENT_ID` - OAuth für Gmail API
- `GMAIL_CLIENT_SECRET` - OAuth für Gmail API
- `GMAIL_REFRESH_TOKEN` - OAuth für Gmail API
- `GITLAB_API_TOKEN` - Für CI Automation

**GitHub Mirror:**
- CLARISSA: `https://github.com/wolfram-laube/clarissa.git` (Push Mirror aktiv)
- Backoffice: Kein Mirror konfiguriert

---

## 📚 Relevante Commits

```
728a3f9b  fix(applications): remove docker-any tag
d2e2d0a5  fix(applications): accept API/web trigger
07c362d0  fix(billing): accept API trigger source
ee3bcc65  docs(runbook): update schedule table
26427529  test(billing): add 55 unit tests
a9b28739  docs(runbook): update index
```

---

## 💬 Prompt für nächsten Chat

```
Kontext: Wir haben gerade die Billing-Migration von CLARISSA nach backoffice 
abgeschlossen und getestet. Alle 3 Workflows (billing, crm-integrity, applications) 
laufen auf dem eigenen Runner in Stockholm.

Lies bitte /mnt/project/HANDOVER_BILLING_TESTS_04_02_2026.md für Details.

Offene Themen:
- CRM Data Quality Issues (Issue #379, unbekannte Labels)
- ADR-002 Testing-Strategie
- Weitere Konsolidierung/Cleanup
```
