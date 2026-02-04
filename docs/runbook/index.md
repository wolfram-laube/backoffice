# Blauweiss Operations Runbook

> **Deppensichere Anleitungen für alle operativen Workflows.**

---

## 🚀 Quick Links

| Ich will... | → | Anleitung |
|-------------|---|-----------|
| **Zeit erfassen** | `/spend 4h 2026-02-04` auf GitLab Issue | [Timesheets](#zeiterfassung) |
| **Rechnung erstellen** | Pipeline triggern | [Billing](billing.md) |
| **Bewerbung verschicken** | Applications Pipeline | [Applications](applications.md) |
| **CRM aktualisieren** | Issue bearbeiten oder Pipeline | [CRM](crm.md) |
| **Fehler beheben** | Logs checken | [Troubleshooting](troubleshooting.md) |

---

## 📊 System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     BLAUWEISS OPERATIONS                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ Zeiterfassung│───▶│  Timesheets │───▶│  Rechnungen │        │
│  │ GitLab/spend │    │   (Typst)   │    │   (Typst)   │        │
│  └─────────────┘    └─────────────┘    └──────┬──────┘        │
│                                                │               │
│                                                ▼               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ Jobportale  │───▶│  Matching   │───▶│ Gmail Drafts│        │
│  │ (Crawl)     │    │   (LLM)     │    │             │        │
│  └─────────────┘    └─────────────┘    └──────┬──────┘        │
│                                                │               │
│                                                ▼               │
│                                         ┌─────────────┐        │
│                                         │Google Drive │        │
│                                         │   Upload    │        │
│                                         └─────────────┘        │
│                                                                 │
│  ┌─────────────────────────────────────────────────────┐      │
│  │                    CRM (GitLab Issues)              │      │
│  │  - 185 Bewerbungen als Issues                       │      │
│  │  - Labels für Status, Rate, Tech                    │      │
│  │  - Comments für Timeline/Kommunikation              │      │
│  └─────────────────────────────────────────────────────┘      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📅 Automatische Schedules

**Alle Schedules laufen jetzt in backoffice (ops/backoffice).**

| Was | Wann | Schedule ID | Variable |
|-----|------|-------------|----------|
| **Monthly Billing** | 1. des Monats, 06:00 | #4126476 | `BILLING_RUN=true` |
| **Applications Pipeline** | Mo-Fr 08:00 | #4126478 | `APPLICATIONS_PIPELINE=true` |
| **CRM Integrity Check** | Mo 07:00 | #4126477 | `CRM_INTEGRITY_CHECK=true` |
| **CRM Automation** | Daily 08:00 | #4126456 | - |
| **CRM Weekly Report** | Mo 09:00 | #4126452 | - |
| **CRM Monthly Report** | 1. des Monats, 09:00 | #4126453 | - |

---

## 👥 Team & Rollen

| Person | Rolle | GitLab User | Verantwortung |
|--------|-------|-------------|---------------|
| **Wolfram Laube** | Solution Architect | `wolfram_laube` | Owner, alle Workflows |
| **Ian Matejka** | AI Engineer | `ian.matejka` | Research, AI/ML |
| **Michael Matejka** | Project Manager | `michael.matejka` | Contracts, Kunden |

---

## 📁 Repository-Struktur

| Repo | Project ID | Zweck |
|------|------------|-------|
| **ops/backoffice** | 77555895 | Alle Business Operations |
| **ops/crm** | 78171527 | GitLab Issues als CRM |
| **ops/corporate** | 77075415 | ADRs, Legal, Branding |
| **projects/clarissa** | 77260390 | Research only |

---

## 🔧 Runbooks nach Domäne

### 💰 Billing & Invoicing

[→ Vollständiges Billing Runbook](billing.md)

**Kurzversion:**

1. **Zeit erfassen:** `/spend Xh YYYY-MM-DD` auf Issue mit `client:xyz` Label
2. **Timesheet generieren:** Automatisch am 1. des Monats ODER manuell via Portal
3. **Rechnung erstellen:** Pipeline mit `GENERATE_INVOICE=true`
4. **Prüfen & Upload:** PDF landet automatisch in Google Drive

### 📋 Applications & Jobsuche  

[→ Vollständiges Applications Runbook](applications.md)

**Kurzversion:**

1. **Crawl:** Freelancermap-Projekte werden täglich (Mo-Fr 08:00) gescraped
2. **Match:** LLM bewertet Match gegen Profile
3. **Draft:** Gmail-Entwürfe werden erstellt
4. **CRM:** Issue wird angelegt/aktualisiert

### 🗂️ CRM

[→ Vollständiges CRM Runbook](crm.md)

**Kurzversion:**

- **Board:** https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/boards/10081703
- **Hot Leads:** Filter mit Label `hot-lead`
- **Status ändern:** Label tauschen (drag & drop im Board)
- **Kommunikation:** Als Comment auf Issue dokumentieren

---

## 🔗 Wichtige Links

| Resource | URL |
|----------|-----|
| **Operations Portal** | https://irena-40cc50.gitlab.io/portal.html |
| **CRM Board** | https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/boards/10081703 |
| **Hot Leads** | https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/issues?label_name[]=hot-lead |
| **ADRs** | https://gitlab.com/wolfram_laube/blauweiss_llc/ops/corporate/-/tree/main/docs/adr |
| **Google Drive** | BLAUWEISS-EDV-LLC Shared Drive |

---

## 🆘 Troubleshooting

[→ Vollständiges Troubleshooting Runbook](troubleshooting.md)

### Quick Fixes

| Problem | Lösung |
|---------|--------|
| Pipeline hängt | Check Runner Status auf GitLab |
| Google Drive Upload failed | Credentials in CI vars prüfen |
| CRM Integrity Check failed | Logs lesen, meistens Label-Typos |
| Gmail Draft nicht erstellt | `DRAFTS_JSON_B64` Variable prüfen |

---

## 📝 Änderungshistorie

| Datum | Änderung | Autor |
|-------|----------|-------|
| 2026-02-04 | Initial version | Wolfram + Claude |
| 2026-02-04 | Billing nach backoffice migriert | Wolfram + Claude |
| 2026-02-04 | Alle Schedules nach backoffice migriert | Wolfram + Claude |
