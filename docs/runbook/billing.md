# Billing Runbook

> Von der Zeiterfassung zur Rechnung - Schritt für Schritt.

---

## Quick Reference

| Item | Value |
|------|-------|
| **Repo** | projects/clarissa (→ backoffice nach Migration) |
| **Pipeline** | `.gitlab-ci.yml` (Jobs: `generate_timesheets`, `build_invoice`, `upload_invoice`) |
| **Schedule** | #4094512 (1. des Monats, 06:00 Vienna) |
| **Trigger URL** | [Portal → Billing](https://irena-40cc50.gitlab.io/docs/billing-trigger.html) |
| **Google Drive** | BLAUWEISS-EDV-LLC → Buchhaltung/ |
| **Owner** | Wolfram |

---

## Übersicht: Der Billing-Zyklus

```
┌──────────────────────────────────────────────────────────────────┐
│                      MONATLICHER BILLING-ZYKLUS                  │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  LAUFEND (während des Monats)                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  /spend 4h 2026-01-15                                   │    │
│  │  /spend 2h30m 2026-01-16                                │    │
│  │  ...                                                     │    │
│  │  (auf Issues mit Label "client:xyz")                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│                           ▼                                      │
│  AM 1. DES FOLGEMONATS (automatisch 06:00)                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  1. generate_timesheet.py                               │    │
│  │     └─▶ Wolfram_nemensis_2026-01_timesheet.typ         │    │
│  │     └─▶ Ian_nemensis_2026-01_timesheet.typ             │    │
│  │                                                         │    │
│  │  2. typst compile *.typ → *.pdf                        │    │
│  │                                                         │    │
│  │  3. upload_to_drive.py                                  │    │
│  │     └─▶ Buchhaltung/contractors/{person}/2026/01/      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│                           ▼                                      │
│  MANUELL (nach Timesheet-Freigabe)                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  4. generate_invoice.py --client nemensis              │    │
│  │     └─▶ nemensis_2026-01_invoice_AR_042.typ            │    │
│  │                                                         │    │
│  │  5. typst compile → PDF                                 │    │
│  │                                                         │    │
│  │  6. upload_to_drive.py                                  │    │
│  │     └─▶ Buchhaltung/clients/nemensis/2026/01/          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Teil 1: Zeiterfassung

### Voraussetzungen

- [ ] GitLab Issue existiert für die Arbeit
- [ ] Issue hat Label `client:xyz` (z.B. `client:nemensis`)
- [ ] Du bist eingeloggt als der richtige GitLab User

### Happy Path: Zeit erfassen

**Auf dem GitLab Issue einen Comment schreiben:**

```
/spend 4h 2026-01-15
```

**Format:**
- `Xh` = Stunden (z.B. `4h`, `8h`)
- `Xm` = Minuten (z.B. `30m`)
- `XhYm` = Kombination (z.B. `2h30m`)
- `YYYY-MM-DD` = Datum (MUSS angegeben werden!)

**Beispiele:**

```
/spend 8h 2026-01-15           # Ganzer Tag
/spend 4h30m 2026-01-16        # Halber Tag + Pause
/spend 2h 2026-01-17           # Kurzer Einsatz
```

### Zeiterfassung prüfen

**Option A: Auf dem Issue**

Rechte Sidebar → "Time tracking" zeigt Gesamtzeit.

**Option B: Via API (für Details)**

```bash
curl -s --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/77260390/issues/36/timelogs" | jq
```

### Korrektur: Zeit entfernen

**Negativer /spend:**

```
/spend -2h 2026-01-15
```

⚠️ **Achtung:** Das Datum muss mit dem Original übereinstimmen!

---

## Teil 2: Timesheet generieren

### Automatisch (Standard)

Die Pipeline läuft automatisch am **1. des Monats um 06:00** (Vienna Time).

**Was passiert:**
1. GraphQL API holt alle Time Entries für den Vormonat
2. Gruppiert nach Client und Consultant
3. Generiert Typst-Dateien
4. Kompiliert zu PDF
5. Uploaded nach Google Drive

**Prüfen ob's geklappt hat:**
- Pipeline: https://gitlab.com/wolfram_laube/blauweiss_llc/projects/clarissa/-/pipelines
- Google Drive: `Buchhaltung/contractors/{person}/{year}/{month}/`

### Manuell triggern

**Option A: Via Portal**

1. Öffne https://irena-40cc50.gitlab.io/docs/billing-trigger.html
2. Wähle Periode (z.B. `2026-01`)
3. Klick "Generate Timesheets"

**Option B: Via API**

```bash
curl -X POST \
  -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ref":"main","variables":[{"key":"GENERATE_TIMESHEETS","value":"true"},{"key":"BILLING_PERIOD","value":"2026-01"}]}' \
  "https://gitlab.com/api/v4/projects/77260390/pipeline"
```

**Option C: Via GitLab UI**

1. Gehe zu CLARISSA → CI/CD → Pipelines
2. "Run pipeline"
3. Variables:
   - `GENERATE_TIMESHEETS` = `true`
   - `BILLING_PERIOD` = `2026-01` (optional, default = Vormonat)

---

## Teil 3: Rechnung erstellen

### Voraussetzungen

- [ ] Timesheets für alle Consultants sind generiert
- [ ] Timesheets sind vom Kunden freigegeben (falls erforderlich)
- [ ] Rechnungsnummer ist bekannt (aus `sequences.yaml`)

### Happy Path: Rechnung generieren

**Via API:**

```bash
curl -X POST \
  -H "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ref":"main","variables":[{"key":"GENERATE_INVOICE","value":"true"},{"key":"INVOICE_CLIENT","value":"nemensis"},{"key":"BILLING_PERIOD","value":"2026-01"}]}' \
  "https://gitlab.com/api/v4/projects/77260390/pipeline"
```

**Was passiert:**
1. Liest alle Timesheets für den Client
2. Konsolidiert Team-Stunden (Einzelstunden bleiben intern)
3. Generiert Rechnung mit nächster Rechnungsnummer
4. Kompiliert zu PDF
5. Uploaded nach Google Drive: `Buchhaltung/clients/{client}/{year}/{month}/`

### Rechnungstypen

| Typ | Template | Verwendung |
|-----|----------|------------|
| **DE** | `rechnung-de.typ` | Deutsche Kunden (mit MwSt) |
| **EU** | `invoice-en-eu.typ` | EU-Kunden (Reverse Charge) |
| **US** | `invoice-en-us.typ` | US-Kunden (no VAT) |

Der Typ wird aus `clients.yaml` gelesen.

---

## Teil 4: Sonderfälle

### Szenario A: Einzelperson (nur Wolfram)

Standard-Fall. Timesheet = Rechnung (gleiche Stunden).

### Szenario B: Team-Projekt (Wolfram + Ian)

1. Beide erfassen Zeit auf Issues mit gleichem `client:xyz` Label
2. Pipeline generiert **separate Timesheets** pro Person
3. Rechnung zeigt **konsolidierte Team-Stunden** (ohne Einzelaufschlüsselung)
4. Interne Abrechnung: Jeder stellt der LLC ein Honorar

**Ordnerstruktur:**
```
Buchhaltung/
├── clients/nemensis/2026/01/
│   ├── invoice_AR_042.pdf        # Kundenrechnung (konsolidiert)
│   └── timesheet_team.pdf        # Team-Timesheet für Kunden
│
└── contractors/
    ├── wolfram/2026/01/nemensis/
    │   ├── timesheet.pdf         # Wolframs Stunden
    │   └── honorar.pdf           # Wolframs Honorarnote an LLC
    │
    └── ian/2026/01/nemensis/
        ├── timesheet.pdf         # Ians Stunden
        └── honorar.pdf           # Ians Honorarnote an LLC
```

### Szenario C: Nachträgliche Korrektur

**Fall 1: Vergessene Stunden nachtragen**

```
/spend 4h 2026-01-20
```
→ Timesheet neu generieren (überschreibt das alte)

**Fall 2: Zu viele Stunden eingetragen**

```
/spend -2h 2026-01-20
```
→ Timesheet neu generieren

**Fall 3: Rechnung schon versendet, Fehler gefunden**

1. Stornorechnung erstellen (negative Beträge)
2. Korrigierte Rechnung mit neuer Nummer erstellen
3. Beide an Kunden senden

---

## Konfiguration

### clients.yaml

```yaml
consultants:
  wolfram:
    name: "Wolfram Laube"
    gitlab_username: "wolfram_laube"
  ian:
    name: "Ian Matejka"
    gitlab_username: "ian.matejka"

clients:
  nemensis:
    name: "nemensis AG Deutschland"
    gitlab_label: "client:nemensis"
    invoice_type: "eu"           # eu, de, us
    rates:
      remote: 105
      onsite: 120
    consultants:
      - wolfram
      - ian
    address:
      company: "nemensis AG"
      street: "Musterstraße 1"
      city: "12345 München"
      country: "Germany"
    contact:
      name: "Max Mustermann"
      email: "m.mustermann@nemensis.de"
```

### sequences.yaml

```yaml
invoices:
  prefix: "AR"
  next_number: 43
  format: "{prefix}-{number:03d}"   # AR-043
```

---

## Troubleshooting

### Problem: "No time entries found"

**Symptom:** Pipeline läuft durch, aber Timesheet ist leer.

**Ursachen:**
1. Falsches Label auf den Issues
2. Zeitraum falsch (BILLING_PERIOD)
3. `/spend` ohne Datum → landet auf "heute", nicht im Abrechnungsmonat

**Fix:**
```bash
# Prüfen welche Labels existieren
curl -s --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/groups/120698013/labels" | jq '.[].name' | grep client
```

### Problem: "GraphQL returned null"

**Symptom:** API-Error in Pipeline Logs.

**Ursache:** GitLab Token abgelaufen oder keine Berechtigung.

**Fix:**
1. Neuen PAT erstellen auf GitLab
2. CI Variable `GITLAB_TOKEN` aktualisieren

### Problem: "Google Drive upload failed"

**Symptom:** PDF wurde generiert aber nicht hochgeladen.

**Ursachen:**
1. Service Account Credentials ungültig
2. Shared Drive Berechtigung fehlt
3. Folder ID falsch

**Fix:**
```bash
# Test Google Drive Connection
python billing/scripts/upload_to_drive.py --test
```

### Problem: "Typst compilation failed"

**Symptom:** .typ Datei existiert, aber kein PDF.

**Ursache:** Syntax-Error im Template oder fehlende Fonts.

**Fix:**
```bash
# Lokal testen
typst compile billing/output/test.typ
```

---

## Referenzen

- **ADR:** [OPS-001: Billing Migration](../adr/operations/OPS-001-billing-migration.md)
- **Folder Structure:** [CLARISSA ADR-019](https://gitlab.com/wolfram_laube/blauweiss_llc/projects/clarissa/-/blob/main/docs/architecture/adr/ADR-019-billing-folder-structure.md)
- **Schedule:** https://gitlab.com/wolfram_laube/blauweiss_llc/projects/clarissa/-/pipeline_schedules/4094512
- **Google Drive:** BLAUWEISS-EDV-LLC Shared Drive

---

## Änderungshistorie

| Datum | Änderung | Autor |
|-------|----------|-------|
| 2026-02-04 | Initial version | Wolfram + Claude |
