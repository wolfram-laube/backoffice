# NEXT SESSION PROMPT

Lies zuerst das Handover:
- `docs/handover/HANDOVER_QUARTO_PIPELINE_07_02_2026.md`
- `docs/handover/HANDOVER_NSAI_V030_06_02_2026.md` (Kontext)

## Kontext

NSAI Paper v3 ist fertig (LaTeX + Quarto). Ein paradigmatischer Quarto Publication Flow wurde gebaut und getestet. Beides muss noch committed werden.

## Aufgaben (Prioritaet)

### 1. Quarto-Projekt committen (backoffice)

Erstelle `docs/publications/nsai-runner-selection-2026/` mit:
- `_quarto.yml`
- `experiment.qmd`
- `nsai_paper.qmd`
- `references.bib`
- `figures/fig1_architecture.pdf` + `fig6_dialectic.pdf` (nur statische)
- `.gitignore` mit `_output/`

Die generierten Figures (fig2-5, fig7) werden von experiment.qmd erzeugt und NICHT committed.

Commit-Message: `docs(publications): add NSAI paper as Quarto project (GOV-003)`

### 2. GOV-003 committen (corporate)

`docs/adr/governance/GOV-003-publication-workflow.md`

Commit-Message: `docs(adr): GOV-003 publication workflow with Quarto`

### 3. Pipeline #495 Cloud Run Deploy

Status checken — braucht aktiven Runner (Mac oder Nordic). Falls einer online:
```
POST /api/v4/projects/77555895/pipelines/495/jobs/{job_id}/play
```

### 4. Issue #26 Status-Update

NSAI Experiment Notebook ist fertig. Comment mit Zusammenfassung der Ergebnisse posten.

### 5. CI-Job fuer Publication Build (optional)

In `backoffice/.gitlab-ci.yml` einen `publication:build` Job anlegen der:
- Quarto installiert
- `quarto render` ausfuehrt
- PDF als Artifact exportiert
- Nur bei Aenderungen in `docs/publications/` triggert

## Credentials

- GitLab PAT: `glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj`
- User: wolfram.laube (ID: 1349601)
- Repos: backoffice=77555895, corporate=77075415, CLARISSA=77260390
