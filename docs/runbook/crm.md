# CRM Runbook

> Bewerbungen tracken mit GitLab Issues.

---

## Quick Reference

| Item | Value |
|------|-------|
| **Repo** | ops/crm (78171527) |
| **Board** | https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/boards/10081703 |
| **Issues** | 185 Bewerbungen (Stand 02.02.2026) |
| **Labels** | 44 Group-Level Labels |
| **Integrity Check** | Schedule #4125129 (Mo 07:00) |
| **Owner** | Wolfram |

---

## Konzept

```
┌────────────────────────────────────────────────────────────────┐
│                      CRM = GitLab Issues                       │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Issue = Eine Bewerbung                                       │
│  ├── Title: "DevOps Engineer @ Hays"                          │
│  ├── Labels: status, rate, tech, branche                      │
│  ├── Description: Meta-Daten, Anforderungen, Match-Analyse    │
│  └── Comments: Timeline (Bewerbung → Antwort → Interview)     │
│                                                                │
│  Board = Kanban-Ansicht                                       │
│  └── Spalten = Status-Labels                                  │
│                                                                │
│  Related Issues = Gleiches Projekt, andere Agentur            │
│  └── "KONSENS" bei 5 verschiedenen Agenturen                  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## Board-Spalten (Kanban)

| Spalte | Label | Bedeutung |
|--------|-------|-----------|
| **Neu** | `status::neu` | Draft erstellt, noch nicht versendet |
| **Versendet** | `status::versendet` | Bewerbung abgeschickt |
| **Beim Kunden** | `status::beim-kunden` | Agentur hat ans Endkunden weitergeleitet |
| **Interview** | `status::interview` | Gespräch geplant/durchgeführt |
| **Verhandlung** | `status::verhandlung` | Vertragsverhandlung läuft |
| **Zusage** | `status::zusage` | 🎉 Gewonnen |
| **Absage** | `status::absage` | ❌ Nicht geklappt |
| **Ghost** | `status::ghost` | Keine Reaktion seit 30+ Tagen |

---

## Teil 1: Issue erstellen (manuell)

### Neues Issue anlegen

1. Gehe zu: https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/issues/new
2. Fülle aus:

**Title:**
```
{Position} @ {Agentur}
```
Beispiel: `Senior DevOps Engineer @ Hays`

**Description:**
```markdown
### Meta
- **Agentur:** Hays
- **Kontakt:** Max Mustermann
- **Email:** max@hays.de
- **Telefon:** +49 123 456789
- **Projekt-ID:** FM-12345
- **Rate:** 105 €/h
- **Match:** 85%
- **Start:** ASAP
- **Laufzeit:** 12 Monate
- **Remote:** 100%
- **Standort:** München

### Anforderungen
- Kubernetes, Terraform, AWS
- 5+ Jahre DevOps-Erfahrung
- CI/CD Pipelines

### Match-Analyse
✅ Kubernetes: CKA/CKAD zertifiziert
✅ AWS: 3+ Jahre
⚠️ Terraform: nur Basics

### Related
- #42 (gleiche Position bei Computer Futures)
```

**Labels:**
- `status::neu`
- `rate::105+`
- `tech::kubernetes`
- `tech::aws`
- `branche::banking`
- `remote::100%`

---

## Teil 2: Status ändern

### Option A: Drag & Drop im Board

1. Öffne Board: https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/boards/10081703
2. Ziehe Issue von einer Spalte zur anderen
3. Label wird automatisch getauscht

### Option B: Via Issue-Seite

1. Öffne das Issue
2. Rechte Sidebar → Labels
3. Entferne altes Status-Label
4. Füge neues Status-Label hinzu

### Option C: Via Quick Action

Comment auf Issue:
```
/label ~"status::beim-kunden"
/unlabel ~"status::versendet"
```

---

## Teil 3: Timeline dokumentieren

### Kommunikation als Comments

Jede Interaktion wird als Comment dokumentiert:

```markdown
📤 **04.02.2026 — Bewerbung versendet** (via freelancermap)
Standardbewerbung mit Fokus auf Kubernetes-Erfahrung.

---

📩 **05.02.2026 — Antwort Agentur**
> Vielen Dank, Ihr Profil wird dem Kunden vorgestellt.

---

📩 **07.02.2026 — Kundenfeedback**
Kunde findet Profil "sehr interessant". Interview wird geplant.

---

🎤 **10.02.2026 — Interview**
30min Video-Call mit Teamlead.
- Technische Fragen: Kubernetes, CI/CD ✅
- Kulturfit: Gut
- Nächster Schritt: Entscheidung bis 15.02.

---

✅ **12.02.2026 — Zusage**
Vertrag kommt per Mail. Start 01.03.2026.
```

### Emoji-Legende

| Emoji | Bedeutung |
|-------|-----------|
| 📤 | Ausgehend (Bewerbung, Nachfrage) |
| 📩 | Eingehend (Antwort, Feedback) |
| 🎤 | Interview/Call |
| ✅ | Positive Entwicklung |
| ❌ | Negative Entwicklung |
| ⏰ | Reminder/Follow-up |

---

## Teil 4: Suchen & Filtern

### Hot Leads finden

```
https://gitlab.com/.../ops/crm/-/issues?label_name[]=hot-lead
```

### Nach Technologie

```
https://gitlab.com/.../ops/crm/-/issues?label_name[]=tech::kubernetes
```

### Nach Rate

```
https://gitlab.com/.../ops/crm/-/issues?label_name[]=rate::105+
```

### Kombiniert

```
?label_name[]=status::beim-kunden&label_name[]=rate::105+&label_name[]=remote::100%
```

---

## Teil 5: Integrity Check

### Was wird geprüft (wöchentlich Mo 07:00)

| Check | Beschreibung |
|-------|--------------|
| **Orphan Labels** | Labels ohne Issues |
| **Missing Status** | Issues ohne Status-Label |
| **Multiple Status** | Issues mit >1 Status-Label |
| **Ghost Detection** | "Versendet" ohne Aktivität seit 30 Tagen |
| **Duplicate Check** | Gleicher Titel bei verschiedenen Agenturen |

### Ergebnis prüfen

Pipeline: https://gitlab.com/wolfram_laube/blauweiss_llc/projects/clarissa/-/pipelines

**Exit Codes:**
- `0` = Alles OK ✅
- `1` = Fehler gefunden ❌
- `2` = Warnungen ⚠️

---

## Label-Referenz

### Status (mutually exclusive)

```
status::neu
status::versendet
status::beim-kunden
status::interview
status::verhandlung
status::zusage
status::absage
status::ghost
```

### Rate

```
rate::85-95
rate::95-105
rate::105+
```

### Match Score

```
match::70-80
match::80-90
match::90-100
```

### Remote

```
remote::100%
remote::80%
remote::hybrid
```

### Technologien

```
tech::kubernetes, tech::docker, tech::terraform
tech::aws, tech::azure, tech::gcp
tech::python, tech::java, tech::golang
tech::ci-cd, tech::gitlab, tech::jenkins
tech::kafka, tech::grafana, tech::prometheus
tech::ml-ops, tech::ai
```

### Branchen

```
branche::energie
branche::banking
branche::public-sector
branche::automotive
branche::healthcare
branche::telko
```

### Sonder-Labels

```
hot-lead          # Heißer Kandidat, Priorität!
overpace          # Teilzeit möglich
team-projekt      # Mit Ian/Michael
```

---

## Troubleshooting

### Problem: "Issue nicht im Board sichtbar"

**Ursache:** Kein Status-Label oder falsches Label.

**Fix:** Status-Label hinzufügen.

### Problem: "Duplicate Issues"

**Ursache:** Gleiches Projekt von mehreren Agenturen.

**Fix:** 
1. Als "Related" verknüpfen
2. Primäres Issue behalten, andere als `status::ghost` markieren

### Problem: "Label existiert nicht"

**Ursache:** Labels sind Group-Level, nicht Project-Level.

**Fix:** Labels in der Group erstellen:
https://gitlab.com/groups/wolfram_laube/blauweiss_llc/-/labels

---

## Referenzen

- **Board:** https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/boards/10081703
- **Labels:** https://gitlab.com/groups/wolfram_laube/blauweiss_llc/-/labels
- **Applications Runbook:** [applications.md](applications.md)
- **Integrity Check:** Schedule #4125129

---

## Änderungshistorie

| Datum | Änderung | Autor |
|-------|----------|-------|
| 2026-02-04 | Initial version | Wolfram + Claude |
