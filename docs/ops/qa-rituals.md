# QA Rituals — ops/backoffice

Dieses Dokument beschreibt die Qualitätssicherungs-Rituale für das Bewerbungs-Workflow-System.

## Übersicht

```
┌─────────────────────────────────────────────────────────────┐
│  QA RITUALE                                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  📋 HEALTH CHECK        → Schnell, jederzeit                │
│     Prüft: GitLab API, Gmail OAuth, CRM Zugang              │
│                                                             │
│  🔄 ROUNDTRIP TEST      → Vollständiger Workflow-Test       │
│     Email → CRM Issue → Gmail Draft → Verify                │
│                                                             │
│  🏃 RUNNER CHECK        → Vor wichtigen Jobs                │
│     Prüft: local-shell, gcp-shell Verfügbarkeit             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 1. Health Check

**Wann:** Vor wichtigen Deployments, bei Verdacht auf API-Probleme

**Trigger:**
```bash
# Via Pipeline Variable
RUN_HEALTH_CHECK=true

# Via API
curl -X POST -H "PRIVATE-TOKEN: $TOKEN" \
  "https://gitlab.com/api/v4/projects/77555895/pipeline" \
  -d '{"ref":"main","variables":[{"key":"RUN_HEALTH_CHECK","value":"true"}]}'
```

**Prüft:**
- [ ] GitLab API Authentifizierung
- [ ] Gmail OAuth Token Refresh
- [ ] CRM Projekt Zugang

**Erwartetes Ergebnis:** Alle 3 Checks grün

---

## 2. Roundtrip Test

**Wann:** 
- Wöchentlich (Schedule)
- Nach Änderungen an gmail-drafts.yml, applications.yml
- Nach Credential-Updates

**Trigger:**
```bash
# Via Pipeline Variable
RUN_ROUNDTRIP_TEST=true

# Manuell in GitLab UI
Pipeline → Run Pipeline → Variable: RUN_ROUNDTRIP_TEST = true
```

**Ablauf:**
1. `roundtrip:create-issue` → Erstellt Test-Issue in CRM
2. `roundtrip:create-draft` → Erstellt Gmail Draft
3. `roundtrip:verify` → Prüft beide, schließt Issue

**Erwartetes Ergebnis:**
- CRM Issue erstellt und geschlossen mit Label `status::test-pass`
- Gmail Draft im Postfach sichtbar

**Artefakte:**
- Issue-Kommentar mit Testergebnis
- Pipeline-Log mit Details

---

## 3. Runner Fallback System

**Wann:** Automatisch bei jedem Job der `runner-fallback.yml` included

**Priorität:**
1. `local-shell` → mac#1, mac#2, yoga
2. `gcp-shell` → GCP VM (wird gestartet falls nötig)
3. `gitlab-org-docker` → SaaS Fallback

**Manueller Runner-Check:**
```bash
DEBUG_RUNNERS=true  # Zeigt alle verfügbaren Runner
```

---

## 4. Checkliste: Neuer Workflow-Endpunkt

Bei Hinzufügen eines neuen Integrationsendpunkts:

- [ ] Credentials als Group-Variable anlegen (masked)
- [ ] Health-Check erweitern
- [ ] Roundtrip-Test erweitern
- [ ] Dokumentation aktualisieren

---

## 5. Troubleshooting

### Gmail Draft schlägt fehl (403)

1. Token-Scopes prüfen (braucht `gmail.compose` oder `gmail.modify`)
2. Refresh-Token erneuern falls abgelaufen
3. Google Cloud Console → API aktiviert?

### Runner nicht verfügbar

1. `DEBUG_RUNNERS=true` Pipeline starten
2. Lokale Runner: Laptop-Deckel zu?
3. GCP Runner: VM-Status in GCP Console prüfen

### CRM Issue-Erstellung schlägt fehl

1. `GITLAB_API_TOKEN` gültig?
2. Token-Berechtigungen: `api` scope nötig
3. CRM Projekt-ID korrekt? (78171527)

---

## 6. Schedule-Konfiguration

Empfohlene Pipeline Schedules:

| Schedule | Variable | Frequenz |
|----------|----------|----------|
| Health Check | `RUN_HEALTH_CHECK=true` | Täglich 06:00 |
| Roundtrip Test | `RUN_ROUNDTRIP_TEST=true` | Wöchentlich Mo 07:00 |

Setup in GitLab: CI/CD → Schedules → New Schedule

---

## 7. Metriken

Erfolgsrate der letzten Roundtrip-Tests:
- CRM Issues mit Label `status::test-pass`: ✅
- CRM Issues mit Label `status::test-fail`: ❌

Abfrage:
```bash
curl -s -H "PRIVATE-TOKEN: $TOKEN" \
  "https://gitlab.com/api/v4/projects/78171527/issues?labels=type::roundtrip-test&state=closed" | \
  jq '.[] | {iid, title, labels}'
```

---

*Zuletzt aktualisiert: 2026-02-03*
*Maintainer: ops/backoffice*
