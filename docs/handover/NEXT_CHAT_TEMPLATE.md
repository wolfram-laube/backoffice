# Next Chat Template

Copy & paste für nahtlosen Session-Übergang.

---

## Template

```
Kontext: [Kurzbeschreibung was zuletzt gemacht wurde]

Lies: docs/handover/INDEX.md für Übersicht
Dann: docs/handover/HANDOVER_[TOPIC]_[DATE].md für Details

Credentials:
- GitLab PAT: glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj
- User: wolfram.laube (ID: 1349601)
- GCP SA: claude-assistant@myk8sproject-207017.iam.gserviceaccount.com

Repos:
- ops/backoffice (77555895) - Operations
- ops/crm (78171527) - CRM Issues
- ops/corporate (77075415) - ADRs

Offene Themen:
1. [Topic 1]
2. [Topic 2]

Issues: #XX, #YY
```

---

## Aktueller Stand (2026-02-04)

```
Kontext: CI Runner Migration abgeschlossen, MAB Service deployed, NSAI Epic angelegt.

Lies: docs/handover/INDEX.md für Übersicht
Dann: docs/handover/HANDOVER_PROFILES_CI_04_02_2026.md für Details

Credentials:
- GitLab PAT: glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj
- User: wolfram.laube (ID: 1349601)
- GCP SA: claude-assistant@myk8sproject-207017.iam.gserviceaccount.com

Repos:
- ops/backoffice (77555895) - Operations + runner_bandit Service
- ops/crm (78171527) - CRM Issues
- ops/corporate (77075415) - ADRs

Offene Themen:
1. MAB Service deployen (GCP Cloud Run)
2. GitLab Webhooks für Job-Events konfigurieren
3. NSAI Epic #27 (wenn MAB Baseline stabil)

Issues: #27 (NSAI Epic), #28 (MAB Baseline), #22-26 (NSAI Sub-Issues)
```

---

## Keywords

template, next-chat, workflow, credentials, handover, transition, prompt
