# NEXT SESSION PROMPT

Lies zuerst das Handover:
- `docs/handover/HANDOVER_VORHOELLE_V02_07_02_2026.md`

## Kontext

Match Staging Service "Vorhölle" wurde designed und implementiert (v0.2).
Scaffolding steht, DB Persistence Layer mit 72 Tests, Labels erstellt,
Live-Testing mit 97% Cloud Architect Match durchgeführt.
ADR OPS-004 dokumentiert die Architektur.

## Aufgaben (Priorität)

### 1. Issue #48 Checkboxen updaten

v0.1 und v0.2 DB-Teil sind weitgehend erledigt. Checkboxen in Issue #48 aktualisieren.

### 2. Pipeline-Integration (v0.1 finalisieren)

Der Search→Match→Draft Cycle soll `POST /api/v1/matches` aufrufen statt direkt Drafts zu produzieren.
Prüfen wo der aktuelle Match-Workflow lebt und den Staging-Call einbauen.

### 3. Email Notification (v0.2)

- Gmail API OAuth mit existierendem `credentials.json`
- HTML Template Rendering testen
- Test-Email senden

### 4. Cloud Run Deploy (v0.4)

- Dockerfile ist vorhanden
- Pipeline-Job analog zu runner-bandit Service
- `services/match-staging/` → GCP Artifact Registry → Cloud Run

### 5. Bewerbungen

- CSV-Tracking aktualisieren (bewerbungen_komplett_SORTED_*.csv)
- 5 neue High-Quality Matches aus der Session prüfen (97% Cloud Architect!)
- Amoria Bond Lead weiterverfolgen

## Credentials

- GitLab PAT: `glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj`
- User: wolfram.laube (ID: 1349601)
- Repos: backoffice=77555895, corporate=77075415, CLARISSA=77260390
