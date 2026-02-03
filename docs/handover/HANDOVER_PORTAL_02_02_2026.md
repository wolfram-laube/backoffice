# HANDOVER: Operations Portal — 02.02.2026

## Session: "CRM Migration & Portal Launch"

CRM-System vollständig migriert, QA-Automation implementiert, Operations Portal deployed.

---

## ⚠️ P0 NÄCHSTE SESSION: Naming/Branding Fix

**Problem:**
- Pages URL: `irena-40cc50.gitlab.io` (Relikt aus ECLIPSE/IRENA-Zeit)
- Docs Title: "CLARISSA Documentation" (Forschungsprojekt-Name)
- Portal Title: "Blauweiss Operations Portal" (korrekt, aber inkonsistent)
- **Soll sein:** Einheitliches "Blauweiss" Branding

### Option 1: Custom Domain (EMPFOHLEN)
**Aufwand:** 30 Min | **Disruption:** Keine

```
ops.blauweiss-edv.at → GitLab Pages
```

**Schritte:**
1. DNS CNAME: `ops.blauweiss-edv.at` → `wolfram_laube.gitlab.io`
2. GitLab: Settings → Pages → New Domain
3. SSL-Zertifikat wird automatisch erstellt
4. Alte URL funktioniert weiterhin (Redirect optional)

**Pro:** Professionell, keine Breaking Changes
**Con:** Braucht DNS-Zugang

### Option 2: Projekt umbenennen
**Aufwand:** 15 Min | **Disruption:** HOCH

```
clarissa → blauweiss-ops
URL wird: wolfram_laube.gitlab.io/blauweiss_llc/projects/blauweiss-ops/
```

**Schritte:**
1. GitLab: Settings → General → Rename
2. Alle internen Links aktualisieren
3. GitHub Mirror neu konfigurieren

**Pro:** Saubere URL ohne Custom Domain
**Con:** Bricht ALLE bestehenden Links, GitHub-Repo-Name ändert sich

### Option 3: Nur Branding fixen (QUICK WIN)
**Aufwand:** 15 Min | **Disruption:** Keine

URL bleibt `irena-40cc50.gitlab.io`, aber:
- `mkdocs.yml`: `site_name: "Blauweiss Operations"`
- `docs/index.md`: Header anpassen
- `docs/portal.html`: Bereits korrekt
- Alle HTML `<title>` Tags

**Pro:** Schnell, kein Risiko
**Con:** URL bleibt "irena" (unprofessionell)

### Option 4: Neue GitLab Pages Site
**Aufwand:** 1-2 Std | **Disruption:** Mittel

Separates Projekt nur für Portal/Docs:
```
blauweiss_llc/portal/ → wolfram_laube.gitlab.io/blauweiss_llc/portal/
```

**Pro:** Saubere Trennung CLARISSA (Forschung) vs. Operations
**Con:** Mehr Maintenance, Docs-Sync nötig

### Empfehlung

**Kurzfristig:** Option 3 (Branding fix) — heute machbar
**Mittelfristig:** Option 1 (Custom Domain) — wenn DNS verfügbar

---

## Was wurde erledigt

### 1. CRM System (✅ KOMPLETT)
- 185 Issues aus CSV migriert (2 Duplikate bereinigt)
- 8-Spalten Kanban Board (Neu → Zusage Pipeline)
- 44 Group-Level Labels (Status, Rate, Tech, Branche)
- Hot-Lead Tracking (16 aktive)
- Board: https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/boards/10081703

### 2. QA Automation (✅ KOMPLETT)
- `scripts/ci/crm_integrity_check.py` — 13 Checks (Status, Labels, Ghosts, Funnel)
- `scripts/ci/applications_qa.py` — Pipeline-Validierung + CRM-Dedup
- Weekly Schedule #4125129: Mo 07:00 Vienna
- Exit Codes: 0=PASS, 1=FAIL, 2=WARN

### 3. Operations Portal (✅ KOMPLETT)
- `docs/portal.html` — Zentrale Steuerung mit Trigger-Buttons
- `docs/ops/quickstart.md` — "Deppensichere" Bedienungsanleitung
- `docs/ops/crm.md` — CRM System Dokumentation
- `docs/ops/applications-pipeline.md` — Pipeline Dokumentation
- `docs/ops/api-reference.md` — GitLab API Reference
- `docs/triggers/applications-crawl.html` — Crawler Konfiguration

### 4. Schedules (✅ KONFIGURIERT)
| ID | Cron | Beschreibung | Status |
|----|------|--------------|--------|
| #4094512 | `0 6 1 * *` | Monthly Billing | ✅ AKTIV |
| #4125129 | `0 7 * * 1` | CRM Integrity Check | ✅ AKTIV |
| #4125172 | `0 8 * * 1-5` | Applications Pipeline | ⏸️ BEREIT |

### 5. GitHub Sync (✅ FUNKTIONIERT)
- Bidirektional: GitLab ↔ GitHub
- Last sync: 2026-02-02T21:44
- Repo: github.com/wolfram-laube/clarissa

## Live URLs (aktuell)

| Page | URL |
|------|-----|
| Portal Dashboard | https://irena-40cc50.gitlab.io/portal.html |
| Quick Start | https://irena-40cc50.gitlab.io/ops/quickstart/ |
| CRM Docs | https://irena-40cc50.gitlab.io/ops/crm/ |
| API Reference | https://irena-40cc50.gitlab.io/ops/api-reference/ |
| CRM Board | https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/boards/10081703 |
| Hot Leads | https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/issues?label_name[]=hot-lead |

## Offene Aufgaben (Priorisiert)

### P0: Naming/Branding
- [ ] Entscheidung treffen (Option 1-4)
- [ ] Umsetzung

### P1: Funktional
- [ ] Applications Schedule aktivieren (#4125172)
- [ ] CRM Issues mit freelancermap URLs verlinken
- [ ] Billing Pipeline prüfen (billing.yml existiert nicht)

### P2: Polish
- [ ] Weitere Trigger Pages (match.html, drafts.html, crm-integrity.html)
- [ ] Portal Live-Daten via API (braucht CORS-Proxy)
- [ ] Echten Pipeline Trigger Token im Portal einsetzen

## Wichtige IDs

| Resource | ID |
|----------|-----|
| CLARISSA Project | 77260390 |
| CRM Project | 78171527 |
| Group (blauweiss_llc) | 120698013 |
| CRM Board | 10081703 |
| Pipeline Trigger Token | #4821279 |
| Applications Schedule | #4125172 |
| CRM Schedule | #4125129 |
| Billing Schedule | #4094512 |

## Commits dieser Session

```
8f44f1e6  docs: update handover - add P0 naming fix issue
d0dcae2f  docs: add handover document
65957a54  docs: add Quick Start, API Reference and Portal to navigation
626d3cca  feat: add Operations Portal Dashboard with trigger pages
fe9cb8df  docs: add Operations section with CRM and Applications
6509d438  feat: implement QA validation + CRM integrity check scripts
```

## Transcript

Vollständiger Chat-Verlauf: `/mnt/transcripts/2026-02-02-22-01-32-crm-migration-phase1-complete.txt`

---

## Continuation Prompt für nächste Session

```
Lies das Handover-Dokument in /mnt/project/ oder unter docs/handover/HANDOVER_PORTAL_02_02_2026.md im CLARISSA Repo (Project ID 77260390).

Kontext: Wir haben gestern das CRM-System migriert (185 Issues), QA-Automation implementiert, und ein Operations Portal auf GitLab Pages deployed. 

ERSTE AUFGABE: Das Naming/Branding fixen - die Pages-URL ist noch "irena-40cc50.gitlab.io" und die Docs heißen "CLARISSA Documentation", beides falsch. Im Handover sind 4 Optionen beschrieben. Lass uns entscheiden und umsetzen.

Nach dem Naming-Fix: Applications Schedule aktivieren, Billing Pipeline prüfen, weitere Trigger Pages.

GitLab Token: glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj
```
