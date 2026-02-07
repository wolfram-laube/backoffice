# HANDOVER: NSAI Paper & Quarto Publication Pipeline

**Date:** 2026-02-07
**Session:** Paper Finalization + Quarto Paradigmatic Flow
**Author:** Wolfram Laube + Claude

## Was wurde gemacht

### 1. LaTeX Paper v3 — Clean Build Fix

**Problem:** Paper hatte Font-Warning (`T1/cmr/m/scit`), undefined `\euro{}` command, und brauchte 5+ manuelle LaTeX-Passes.

**Loesung:**
- `\textsc{NSAI}` → `\textnormal{\textsc{nsai}}` (upright in italic context)
- `\euro{}` → `€` (UTF-8 literal, kein Extra-Package)
- `\begin{thebibliography}` → `\bibliography{nsai_paper}` + separate `.bib`

**Ergebnis:** 0 Errors, 0 Undefined, 15 Seiten, 15 BibTeX-Einträge, 485K PDF.

### 2. Quarto Publication Pipeline (Paradigmatisch)

**Motivation:** Notebook-Figures und Paper-Source in verschiedenen Repos = manuelles Copy-Problem. LaTeX allein produziert nur PDF. Zukunft braucht Multi-Format + reproduzierbare Figures.

**Loesung:** Quarto als Source of Truth:

| Source | Format | Zeilen |
|--------|--------|--------|
| `experiment.qmd` | Python-Cells + Markdown | 432 |
| `nsai_paper.qmd` | Markdown + LaTeX-Passthrough | 697 |
| `references.bib` | BibTeX | 125 |
| `_quarto.yml` | YAML Config | 30 |

**Build:** `quarto render` (ein Befehl) → 4 Outputs:

| Output | Groesse | Inhalt |
|--------|---------|--------|
| `nsai_paper.pdf` | 258K, 14 S. | Paper (XeLaTeX) |
| `nsai_paper.html` | 1.6M | Interaktives Paper |
| `experiment.pdf` | 495K | Notebook mit Plots |
| `experiment.html` | 1.9M | Interaktives Notebook |

**Figure-Flow:** experiment.qmd Python-Cells → `plt.savefig('figures/fig*.pdf')` → nsai_paper.qmd `![caption](figures/fig*.pdf)` → automatisch eingebunden.

**Freeze-Cache:** `_freeze/` speichert Execution-Ergebnisse. Text-Edit rebuild: 9s statt 59s.

**Quarto-spezifische Konvertierungen:**

| LaTeX | Quarto |
|-------|--------|
| `\section{Foo}\label{sec:foo}` | `# Foo {#sec-foo}` |
| `\Cref{sec:foo}` | `@sec-foo` |
| `\citep{auer2002finite}` | `[@auer2002finite]` |
| `\begin{figure}...\includegraphics` | `![caption](path){#fig-x}` |
| `\begin{table}` | Pipe-Table mit `: {#tbl-x}` |
| `\begin{definition}` | `::: {#def-x}` Div |
| `\begin{algorithm}` | `` ```{=latex} `` Raw Block |

### 3. GOV-003: Publication Workflow ADR

Dokumentiert den Quarto-Flow als Standard fuer alle kuenftigen Publications:

```
backoffice/docs/publications/<paper-slug>/
├── _quarto.yml          # Project config
├── experiment.qmd       # Code + Figures
├── paper.qmd            # Text (Markdown)
├── references.bib       # Bibliography
├── figures/             # Statische Grafiken
├── _output/             # Generiert (gitignored)
└── _freeze/             # Cached (committed)
```

### 4. Vorherige Session (selber Chat)

- NSAI Experiment ausgefuehrt (300 Rounds docker-any, 100 Rounds GCP, seed=42)
- 7 publication-quality Matplotlib Figures generiert
- LaTeX Paper mit echten Ergebnissen befuellt (alle Tabellen)
- Notebook v2 mit eingebetteten Plot-Cells (50 Cells, 85 Tests)
- Interaktive HTML-Dashboard mit Chart.js (dark NSAI aesthetic)
- BibTeX extrahiert (15 Eintraege), Paper recompiled

## Experiment-Ergebnisse (Seed 42)

| Metrik | Rule-Based | Pure MAB | NSAI |
|--------|-----------|----------|------|
| Cumulative Reward (300r) | 721.3 | 820.6 | 787.6 |
| Convergence Round | never | 17 | 77 |
| GCP Reward (100r) | 237.3 | 219.1 | 245.1 |
| GCP Failures | 4 | 14 | 3 |
| Latency | n/a | n/a | 0.019ms |

## Dateien / Artefakte

### Im Outputs-Ordner (zum Download):

| Datei | Beschreibung |
|-------|-------------|
| `nsai_paper_v3.pdf` | LaTeX-Version (final, 15 S.) |
| `nsai_paper_v3.tex` | LaTeX Source |
| `nsai_paper.bib` | BibTeX (15 Eintraege) |
| `nsai_latex_project.zip` | Overleaf-ready Package |
| `nsai_paper_quarto.pdf` | Quarto-Version (14 S.) |
| `nsai_paper_quarto.html` | Interaktives Paper |
| `nsai_experiment_quarto.html` | Interaktives Notebook |
| `nsai-quarto-project.zip` | Quarto Project Template |
| `GOV-003-publication-workflow.md` | ADR Entwurf |
| `nsai_results_interactive.html` | Chart.js Dashboard |
| `nsai_experiment_v2.ipynb` | Jupyter Notebook (50 Cells) |
| `fig1-fig7*.png` | 7 Publication Figures |

### Noch NICHT committed:

- Quarto-Projekt → `backoffice/docs/publications/nsai-runner-selection-2026/`
- GOV-003 → `corporate/docs/adr/governance/GOV-003-publication-workflow.md`

## Offene Punkte

| Prio | Was | Wohin |
|------|-----|-------|
| 🔴 | Quarto-Projekt committen | backoffice |
| 🔴 | GOV-003 committen | corporate |
| 🟡 | Supervisor-Name im Paper | Beide Versionen |
| 🟡 | Pipeline #495 Cloud Run Deploy | Braucht aktiven Runner |
| 🟡 | Issue #26 Status-Update | backoffice |
| 🟢 | CI-Job `publication:build` einrichten | backoffice .gitlab-ci.yml |
| 🟢 | Quarto in Runner-Image installieren | GCP / Docker |

## Technische Notizen

### Quarto Installation
```bash
wget https://github.com/quarto-dev/quarto-cli/releases/download/v1.6.42/quarto-1.6.42-linux-amd64.deb
dpkg -i quarto-1.6.42-linux-amd64.deb
pip install jupyter matplotlib numpy
quarto install tinytex  # Fuer PDF-Output
apt install lmodern     # Font-Package
```

### Bekannte Quarto-Eigenheiten
- `cleveref` NICHT verwenden — Quarto hat eigene Cross-Refs (`@sec-X`, `@fig-X`)
- Custom `\newcommand` nur EINMAL definieren (entweder `_quarto.yml` ODER Paper YAML, nicht beides)
- `header-includes` in `_quarto.yml` wird mit Paper-eigenen merged → Duplikate = Fehler
- Quarto nutzt XeLaTeX (nicht pdflatex) — UTF-8 nativ, `lmodern` automatisch

### Paper-Versionen
- **v3 (LaTeX):** 925 Zeilen, 15 Seiten, 485K — Submission-ready
- **v3 (Quarto):** 697 Zeilen, 14 Seiten, 258K — Neuer Standard
- Inhaltlich identisch, Quarto etwas kompakter durch Pandoc-Formatting

## Credentials (unveraendert)

- GitLab PAT: `glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj`
- Repos: backoffice=77555895, corporate=77075415, CLARISSA=77260390
