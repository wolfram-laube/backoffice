# 📊 CRM — Bewerbungs-Tracking

Das CRM (Customer Relationship Management) für Freelance-Bewerbungen basiert auf **GitLab Issues** mit einem Kanban-Board und automatisierter QA.

## Übersicht

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CRM ARCHITECTURE                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  CSV Import ──→ GitLab Issues ──→ Kanban Board ──→ QA Monitoring       │
│                      │                                                  │
│                      ▼                                                  │
│              Group-Level Labels                                         │
│              (Status, Rate, Tech, Branche)                              │
│                                                                         │
│  Applications Pipeline ──→ CRM Dedup Check ──→ Gmail Drafts            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Quick Links

| Resource | Link |
|----------|------|
| 📋 Kanban Board | [CRM Pipeline Board](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/boards/10081703) |
| 📁 Issues | [Alle Issues](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/issues) |
| 🔥 Hot Leads | [Hot Leads Filter](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/issues?label_name[]=hot-lead) |
| ⚙️ QA Script | [crm_integrity_check.py](https://gitlab.com/wolfram_laube/blauweiss_llc/projects/clarissa/-/blob/main/scripts/ci/crm_integrity_check.py) |

## Pipeline-Status (Kanban-Spalten)

Das Board bildet den Bewerbungs-Funnel ab:

| Status | Beschreibung | Farbe |
|--------|--------------|-------|
| `status::neu` | Noch nicht versendet | 🔵 Blau |
| `status::versendet` | Bewerbung abgeschickt | 🔵 Dunkelblau |
| `status::beim-kunden` | Beim Endkunden in Prüfung | ⚫ Grau |
| `status::interview` | Gespräch vereinbart/stattgefunden | 🟠 Orange |
| `status::verhandlung` | In Vertragsverhandlung | 🟠 Dunkelorange |
| `status::zusage` | Vertrag/Zusage erhalten | 🟢 Grün |
| `status::absage` | Abgelehnt | 🔴 Rot |
| `status::ghost` | Keine Antwort seit >2 Wochen | ⚫ Dunkelgrau |

## Label-System

### Kategorien

```yaml
# Status (genau 1 pro Issue)
status::neu | versendet | beim-kunden | interview | verhandlung | zusage | absage | ghost

# Stundensatz
rate::unter-85 | rate::85-95 | rate::95-105 | rate::105+

# Remote-Anteil
remote::100% | remote::80% | remote::hybrid

# Technologien
tech::python | kubernetes | aws | azure | gcp | java | terraform | kafka | grafana | ml-ops | ai | devops | ci-cd

# Branchen
branche::energie | banking | public-sector | automotive | healthcare | telko

# Spezial
hot-lead      # Aktiv verfolgen!
overpace      # Teilzeit, kombinierbar
team-projekt  # Mit Ian/Michael
```

### Label-Kombinationen

**Typisches High-Value Issue:**
```
status::beim-kunden, hot-lead, rate::105+, remote::80%, tech::kubernetes, tech::python, branche::energie
```

**Teilzeit-Kombination (Overpace):**
```
status::versendet, overpace, rate::95-105, remote::100%, tech::ai
```

## Workflow

### 1. Neue Bewerbung erfassen

**Automatisch (via Applications Pipeline):**
```bash
# Pipeline triggered täglich 08:00
APPLICATIONS_PIPELINE=true → crawl → match → qa → drafts
```

**Manuell:**
1. Issue erstellen in [CRM Projekt](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/issues/new)
2. Titel: `[Agentur] Positionsbezeichnung`
3. Labels setzen: Status + Rate + Tech + Branche
4. Beschreibung nach Template (siehe unten)

### 2. Status-Übergänge

```
neu → versendet → beim-kunden → interview → verhandlung → zusage
                      ↓              ↓            ↓
                   ghost          absage       absage
```

**Drag & Drop im Board** oder Label ändern.

### 3. Hot Lead markieren

Für vielversprechende Leads:
```
/label ~hot-lead
```

**Kriterien für Hot Lead:**

- Positives Feedback vom Kunden
- Interview vereinbart
- Profil wird vorgestellt
- Rate passt (105€+)
- Tech-Stack passt gut

## Issue-Template

```markdown
## 📋 Projektdetails

| Feld | Wert |
|------|------|
| **Agentur** | {Agenturname} |
| **Kontakt** | {Name} |
| **Email** | {email@example.com} |
| **Telefon** | {+49 ...} |
| **Standort** | {Remote / Stadt} |
| **Start** | {DD.MM.YYYY} |
| **Laufzeit** | {X Monate} |
| **Auslastung** | {100% / 60% / etc.} |
| **Stundensatz** | {XXX} €/h |

## 📝 Notizen

{Freitext für Timeline, Gesprächsnotizen, etc.}
```

## QA & Monitoring

### Automatische Checks (Weekly)

Der `crm:integrity-check` Job läuft jeden **Montag 07:00 Uhr**:

```yaml
Schedule: 0 7 * * 1 (Europe/Vienna)
Variable: CRM_INTEGRITY_CHECK=true
```

**Checks:**

| Check | Beschreibung |
|-------|--------------|
| `status.all_have_one` | Jedes Issue hat genau 1 Status-Label |
| `status.no_multiples` | Keine Issues mit mehreren Status |
| `labels.all_valid` | Alle Labels existieren in Group |
| `dupes.titles` | Keine Titel-Duplikate |
| `ghost.stale_versendet` | Issues ohne Update seit >14 Tagen |
| `funnel.active` | Aktive Pipeline-Größe |
| `rate.coverage` | Rate-Label Abdeckung (Ziel: >90%) |
| `hotleads.no_stale` | Keine Hot Leads mit Absage-Status |

### Manueller Check

```bash
# Pipeline triggern
curl -X POST \
  -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/77260390/pipeline" \
  -d '{"ref":"main","variables":[{"key":"CRM_QA","value":"true"}]}'
```

### Exit Codes

| Code | Bedeutung | Aktion |
|------|-----------|--------|
| 0 | Alle Checks bestanden | ✅ Healthy |
| 1 | Kritische Fehler | ❌ Untersuchen |
| 2 | Nur Warnungen | ⚠️ Optional fixen |

## Metriken

### Funnel Health

```
Conversion Rate = Zusagen / Total Issues
Active Rate = (Versendet + Kunde + Interview + Verhandlung) / Total
Loss Rate = (Absage + Ghost) / Total
```

### Aktuelle Werte (Stand: 02.02.2026)

```
Total:      185 Issues
Pipeline:   6 Neu → 146 Versendet → 6 Kunde → 3 Interview → 1 Verhandlung → 1 Zusage
Absagen:    22 (11.9%)
Hot Leads:  16 aktiv
Coverage:   Rate 96% | Tech 93% | Remote 86%
```

## Integration mit Applications Pipeline

Die Applications Pipeline prüft vor dem Erstellen von Gmail-Drafts gegen das CRM:

```yaml
# .gitlab/applications.yml
applications:qa:
  script:
    - python3 scripts/ci/applications_qa.py --crm-dedup
```

**CRM Dedup Check:**

- Vergleicht Match-Titel mit existierenden Issues
- Markiert bereits beworbene Projekte
- Verhindert Doppel-Bewerbungen

## Troubleshooting

### Issue hat keinen Status

```bash
# Alle Issues ohne Status finden
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://gitlab.com/api/v4/projects/78171527/issues?per_page=100" | \
  jq '.[] | select(.labels | map(startswith("status::")) | any | not) | .iid'
```

### Hot Lead mit Absage

```bash
# Hot-Lead Label entfernen
curl -X PUT -H "PRIVATE-TOKEN: $TOKEN" \
  "https://gitlab.com/api/v4/projects/78171527/issues/{IID}" \
  -d "remove_labels=hot-lead"
```

### Ghost-Status setzen

Für Issues ohne Antwort seit >2 Wochen:

```bash
# Status ändern
curl -X PUT -H "PRIVATE-TOKEN: $TOKEN" \
  "https://gitlab.com/api/v4/projects/78171527/issues/{IID}" \
  -d "remove_labels=status::versendet" \
  -d "add_labels=status::ghost"
```

## Architektur-Entscheidungen

Siehe [ADR-018: GitLab PM Workflow](../architecture/adr/ADR-018-gitlab-pm-workflow.md) für die Grundlagen.

**Warum GitLab Issues statt dediziertes CRM?**

1. **Single Source of Truth** — alles in einem System
2. **API-First** — volle Automatisierung möglich
3. **Kostenlos** — keine zusätzlichen Tools
4. **Versioniert** — Issues haben History
5. **Integriert** — mit CI/CD, Pages, Pipelines

## Nächste Schritte

- [ ] Dashboard mit Funnel-Visualisierung
- [ ] Automatische Ghost-Erkennung mit Notification
- [ ] Team-Zuweisung für Ian/Michael Issues
- [ ] Rate-Verhandlungs-Tracking
