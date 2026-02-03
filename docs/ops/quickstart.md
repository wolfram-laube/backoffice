# 🚀 Quick Start: Blauweiss Operations Portal

**Die komplette Schritt-für-Schritt Anleitung für alle Portal-Funktionen.**

---

## 📋 Inhaltsverzeichnis

1. [Portal aufrufen](#1-portal-aufrufen)
2. [Neue Projekte finden (Applications Pipeline)](#2-neue-projekte-finden)
3. [Bewerbungen verwalten (CRM)](#3-bewerbungen-verwalten)
4. [Zeiterfassung & Rechnungen (Billing)](#4-zeiterfassung--rechnungen)
5. [Entwicklungsumgebungen starten](#5-entwicklungsumgebungen)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Portal aufrufen

### Direkt-Links

| Was | URL |
|-----|-----|
| **Portal Dashboard** | [irena-40cc50.gitlab.io/portal.html](https://irena-40cc50.gitlab.io/portal.html) |
| **CRM Board** | [gitlab.com/.../crm/-/boards/10081703](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/boards/10081703) |
| **Hot Leads** | [gitlab.com/.../issues?label_name[]=hot-lead](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/issues?label_name[]=hot-lead) |
| **Pipelines** | [gitlab.com/.../pipelines](https://gitlab.com/wolfram_laube/blauweiss_llc/projects/clarissa/-/pipelines) |

### Bookmark setzen

1. Öffne das Portal: `https://irena-40cc50.gitlab.io/portal.html`
2. Drücke `Strg+D` (Windows) oder `Cmd+D` (Mac)
3. Speichere als "Blauweiss Portal"

---

## 2. Neue Projekte finden

### 🔄 Automatisch (empfohlen)

Die Pipeline läuft automatisch **Mo-Fr um 08:00 Uhr**:

1. **Crawl**: Sucht neue Projekte auf freelancermap.de
2. **Match**: Bewertet Projekte nach deinem Profil
3. **QA**: Prüft auf Duplikate und Qualität
4. **Drafts**: Erstellt Gmail-Entwürfe

**Ergebnis**: Jeden Morgen liegen 5 neue E-Mail-Entwürfe in Gmail.

### 🖱️ Manuell starten

#### Option A: Portal (einfach)

1. Öffne das [Portal](https://irena-40cc50.gitlab.io/portal.html)
2. Klicke auf **"▶️ Volle Pipeline"** unter "Full Pipeline"
3. Warte 2-3 Minuten
4. Prüfe Gmail auf neue Entwürfe

#### Option B: GitLab UI

1. Gehe zu [Pipelines](https://gitlab.com/wolfram_laube/blauweiss_llc/projects/clarissa/-/pipelines)
2. Klicke **"Run pipeline"** (blauer Button rechts oben)
3. Wähle Branch: `main`
4. Füge Variable hinzu:
   - Key: `APPLICATIONS_PIPELINE`
   - Value: `true`
5. Klicke **"Run pipeline"**

#### Option C: Terminal

```bash
curl -X POST \
  -F "token=glptt-4o..." \
  -F "ref=main" \
  -F "variables[APPLICATIONS_PIPELINE]=true" \
  "https://gitlab.com/api/v4/projects/77260390/trigger/pipeline"
```

### 📊 Ergebnisse prüfen

Nach der Pipeline:

1. **Gmail öffnen**: Schaue in "Entwürfe"
2. **Entwurf prüfen**: Anschreiben + CV Attachment
3. **Personalisieren**: Bei Bedarf anpassen
4. **Absenden**: Manuell versenden

---

## 3. Bewerbungen verwalten

### 📋 CRM Board verstehen

Das [Kanban Board](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/boards/10081703) hat 8 Spalten:

| Spalte | Bedeutung | Aktion |
|--------|-----------|--------|
| **Neu** | Noch nicht versendet | Bewerbung vorbereiten |
| **Versendet** | Abgeschickt | Auf Antwort warten |
| **Beim Kunden** | Beim Endkunden | Nachfassen nach 1 Woche |
| **Interview** | Gespräch geplant | Vorbereiten! |
| **Verhandlung** | Rate/Vertrag | Verhandeln |
| **Zusage** | 🎉 Gewonnen! | Vertrag unterschreiben |
| **Absage** | Nicht geklappt | Archivieren |
| **Ghost** | Keine Antwort | Nachfassen oder schließen |

### 🖱️ Status ändern

**Drag & Drop:**
1. Öffne das [Board](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/boards/10081703)
2. Ziehe die Karte in die neue Spalte
3. Fertig!

**Oder via Issue:**
1. Öffne das Issue
2. Rechts: Labels → Entferne altes `status::*`
3. Füge neues `status::*` hinzu

### 🔥 Hot Lead markieren

Für vielversprechende Projekte:

1. Öffne das Issue
2. Füge Label hinzu: `hot-lead`
3. Das Issue erscheint jetzt in der [Hot Leads Liste](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/issues?label_name[]=hot-lead)

### ➕ Neue Bewerbung manuell erfassen

1. Gehe zu [Neues Issue](https://gitlab.com/wolfram_laube/blauweiss_llc/ops/crm/-/issues/new)
2. Titel: `[Agenturname] Positionsbezeichnung`
3. Labels setzen:
   - `status::versendet`
   - `rate::105+` (oder passende Rate)
   - `tech::kubernetes` (passende Technologien)
   - `branche::energie` (passende Branche)
4. Beschreibung ausfüllen (Template unten)
5. **"Create issue"** klicken

**Issue-Template:**
```markdown
## 📋 Projektdetails

| Feld | Wert |
|------|------|
| **Agentur** | Agenturname |
| **Kontakt** | Max Mustermann |
| **Email** | max@agentur.de |
| **Telefon** | +49 123 456789 |
| **Standort** | Remote / Frankfurt |
| **Start** | 01.03.2026 |
| **Laufzeit** | 12 Monate |
| **Auslastung** | 100% |
| **Stundensatz** | 105 €/h |

## 📝 Notizen

- Erstkontakt am: DD.MM.YYYY
- Projekt-URL: https://freelancermap.de/...
```

### 📊 CRM Qualitätsprüfung

Läuft automatisch jeden **Montag 07:00 Uhr**.

Manuell starten:
1. Portal → **"CRM Integrity Check"** → **"▶️ Check starten"**
2. Oder: GitLab Pipeline mit `CRM_QA=true`

**Prüft:**
- Jedes Issue hat genau 1 Status-Label
- Keine Duplikate
- Keine "Ghosts" (>2 Wochen ohne Update)
- Hot Leads haben keinen Absage-Status

---

## 4. Zeiterfassung & Rechnungen

### 📅 Automatisch (monatlich)

Am **1. jedes Monats um 06:00 Uhr**:

1. Timesheet wird aus Kalender generiert
2. PDF wird erstellt
3. Upload zu Google Drive
4. Optional: E-Mail-Versand

### 🖱️ Manuell starten

1. Öffne [Billing Trigger](https://irena-40cc50.gitlab.io/billing-trigger.html)
2. Wähle Monat/Jahr
3. Klicke **"Generate Timesheet"**
4. Warte auf E-Mail-Bestätigung

### 📁 Wo finde ich die Rechnungen?

1. Google Drive: `Blauweiss EDV/Billing/YYYY/MM/`
2. Oder: GitLab Artifacts der Billing-Pipeline

---

## 5. Entwicklungsumgebungen

### 🐧 Linux Runner (Yoga) starten

1. Portal → **"Linux Runner"** → **"▶️ Start"**
2. Warte 1-2 Minuten
3. Status prüfen: **"📊 Status"**

### 🍎 Mac Runner (Mac2) starten

1. Portal → **"Mac Runner"** → **"▶️ Start"**
2. Warte 1-2 Minuten
3. Status prüfen: **"📊 Status"**

### ☁️ GCP VM starten

1. Portal → **"GCP VM"** → **"▶️ Start"**
2. VM läuft nach ca. 30 Sekunden
3. **Wichtig**: Nach Nutzung wieder stoppen! (Kostet Geld)

### 🔌 SSH-Zugang

```bash
# Linux Yoga
ssh wolfram@yoga.local

# Mac2
ssh wolfram@mac2.local

# GCP VM
gcloud compute ssh clarissa-runner --zone=europe-west1-b
```

---

## 6. Troubleshooting

### ❌ Pipeline schlägt fehl

1. Öffne die [Pipeline](https://gitlab.com/wolfram_laube/blauweiss_llc/projects/clarissa/-/pipelines)
2. Klicke auf die fehlgeschlagene Pipeline
3. Klicke auf den roten Job
4. Lese die Fehlermeldung
5. Häufige Ursachen:
   - Runner offline → Runner starten (siehe oben)
   - Token abgelaufen → CI/CD Variables prüfen
   - Rate Limit → Später erneut versuchen

### ❌ Gmail Drafts werden nicht erstellt

1. Prüfe: Sind `GMAIL_*` Variablen gesetzt?
   - GitLab → Settings → CI/CD → Variables
2. Prüfe: Ist der Refresh Token noch gültig?
   - [Token erneuern](https://developers.google.com/oauthplayground/)
3. Prüfe: Hat die Pipeline Matches gefunden?
   - Artifacts → `matches.json` prüfen

### ❌ CRM Board zeigt keine Issues

1. Prüfe: Bist du eingeloggt bei GitLab?
2. Prüfe: Hast du Zugriff auf das CRM-Projekt?
3. Prüfe: Filter zurücksetzen (Button oben rechts)

### ❌ Portal-Buttons funktionieren nicht

**CORS-Problem**: Browser blockiert die API-Aufrufe.

**Lösung 1**: Manuell über GitLab triggern (siehe Abschnitt 2)

**Lösung 2**: Terminal verwenden:
```bash
curl -X POST \
  -F "token=DEIN_TRIGGER_TOKEN" \
  -F "ref=main" \
  -F "variables[APPLICATIONS_PIPELINE]=true" \
  "https://gitlab.com/api/v4/projects/77260390/trigger/pipeline"
```

### 🆘 Hilfe holen

1. **Dokumentation**: [irena-40cc50.gitlab.io/ops/](https://irena-40cc50.gitlab.io/ops/)
2. **GitLab Issues**: [Neues Issue erstellen](https://gitlab.com/wolfram_laube/blauweiss_llc/projects/clarissa/-/issues/new)
3. **Chat mit Claude**: Diese Konversation fortsetzen

---

## 📋 Checkliste: Tägliche Routine

```
□ 08:30  Gmail-Entwürfe prüfen (automatisch generiert um 08:00)
□ 08:45  Entwürfe personalisieren und versenden
□ 09:00  Hot Leads checken — Nachfass-Aktionen?
□ 17:00  CRM Board durchgehen — Status-Updates nötig?
```

## 📋 Checkliste: Wöchentliche Routine

```
□ Montag   CRM Integrity Report prüfen (automatisch 07:00)
□ Montag   Ghost-Issues identifizieren → nachfassen oder schließen
□ Freitag  Pipeline-Fehler der Woche analysieren
□ Freitag  Rate-Verhandlungen Status-Update
```

## 📋 Checkliste: Monatliche Routine

```
□ 1.      Billing-Report prüfen (automatisch 06:00)
□ 1.-5.   Rechnungen versenden
□ 15.     Conversion-Rate analysieren
□ 30.     Funnel-Optimierung planen
```

---

**Letzte Aktualisierung**: 02.02.2026  
**Version**: 1.0
