# Next Chat Template

Copy & paste für nahtlosen Session-Übergang.

**WICHTIG:** Die Handover-Dateien liegen im GitLab Repo, NICHT in /mnt/project/!
Claude muss sie via GitLab API lesen (curl mit PAT).

---

## Template

```
Kontext: [Kurzbeschreibung was zuletzt gemacht wurde]

WICHTIG: Handover-Dateien liegen im GitLab Repo, nicht in /mnt/project/!
Lies via API:
  curl -s --header "PRIVATE-TOKEN: $PAT" \
    "https://gitlab.com/api/v4/projects/77555895/repository/files/docs%2Fhandover%2FINDEX.md/raw?ref=main"

Credentials:
- GitLab PAT: glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj
- User: wolfram.laube (ID: 1349601)
- Backoffice Project ID: 77555895
- GCP SA: claude-assistant@myk8sproject-207017.iam.gserviceaccount.com

Repos:
- ops/backoffice (77555895) - Operations
- ops/crm (78171527) - CRM Issues
- ops/corporate (77075415) - ADRs

Handover lesen:
1. INDEX.md: docs/handover/INDEX.md (Übersicht)
2. Detail: docs/handover/HANDOVER_[TOPIC]_[DATE].md

Offene Themen:
1. [Topic 1]
2. [Topic 2]

Issues: #XX, #YY
```

---

## Aktueller Stand (2026-02-04)

```
Kontext: CI Runner Migration abgeschlossen, MAB (Multi-Armed Bandit) Service deployed, NSAI Epic angelegt.

WICHTIG: Handover-Dateien liegen im GitLab Repo, nicht in /mnt/project/!
Lies zuerst via API:
  curl -s --header "PRIVATE-TOKEN: glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj" \
    "https://gitlab.com/api/v4/projects/77555895/repository/files/docs%2Fhandover%2FINDEX.md/raw?ref=main"

Dann Detail:
  curl -s --header "PRIVATE-TOKEN: glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj" \
    "https://gitlab.com/api/v4/projects/77555895/repository/files/docs%2Fhandover%2FHANDOVER_PROFILES_CI_04_02_2026.md/raw?ref=main"

Credentials:
- GitLab PAT: glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj
- User: wolfram.laube (ID: 1349601)
- Backoffice Project ID: 77555895
- GCP SA: claude-assistant@myk8sproject-207017.iam.gserviceaccount.com

Repos:
- ops/backoffice (77555895) - Operations + services/runner_bandit/
- ops/crm (78171527) - CRM Issues
- ops/corporate (77075415) - ADRs

Offene Themen:
1. MAB Service deployen (GCP Cloud Run) - Code liegt in services/runner_bandit/
2. GitLab Webhooks für Job-Events konfigurieren
3. NSAI Epic #27 (wenn MAB Baseline stabil)

MAB = Multi-Armed Bandit (UCB1, Thompson Sampling) für intelligente Runner-Auswahl
NSAI = Neurosymbolic AI Erweiterung (Future Work)

Issues: #27 (NSAI Epic), #28 (MAB Baseline), #22-26 (NSAI Sub-Issues)
```

---

## Keywords

template, next-chat, workflow, credentials, handover, transition, prompt, api, gitlab
