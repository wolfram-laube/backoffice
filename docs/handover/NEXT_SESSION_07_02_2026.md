# Naechste Session: JKU Paper + Cloud Run + Bug Cleanup

## Kontext

NSAI v0.3.0 auf main: Ontology-MAB Alignment, 85 Tests, Experiment-Notebook mit TestSuite (13 Assert-Cells), ADR-027 als Architekturdokumentation. MAB Service hat 83 Observations (nur Nordic), Webhooks aktiv.

## Erledigt (Session 06.02.2026 Abend)

- NSAI v0.3.0: 4 Production Runner, mab_tag Mapping, from_live_service()
- 25 Integration Tests + 60 bestehende = 85 total, alle gruen
- Experiment Notebook mit 13 TestSuite-Cells (JKU-Style)
- A/B Vergleich: NSAI > Rule-Based, sublineare Regret
- ADR-027 NSAI Architecture (HTML, Dialektik-Format)
- ADR Index README
- MR !17 merged, Pipeline sauber (50 Jobs, 0 Failures)
- Issue #47 analysiert + closed

## Offen (Prio-Reihenfolge)

1. **Issue #26: JKU Bachelor Paper Draft** — Experiment-Daten stehen bereit
2. **Cloud Run Redeploy** — GCS Persistence fuer MAB State
3. **Lokale Runner aktivieren** — Mac + Linux Yoga fuer Multi-Runner-Daten
4. **GitHub Mirror** (Issue #29) — Notebook nach GitHub fuer Colab/JKU
5. **Bug Cleanup** — #41 (NSAI setuptools), #42 (integration dir), #34, #43

## Zugang

- GitLab Token: glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj
- GCP Projekt: myk8sproject-207017
- MAB Service: https://runner-bandit-m5cziijwqa-lz.a.run.app/

## Handover lesen

```
curl -sf --header "PRIVATE-TOKEN: glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj" \
  "https://gitlab.com/api/v4/projects/77555895/repository/files/docs%2Fhandover%2FHANDOVER_NSAI_V030_06_02_2026.md/raw?ref=main"
```
