# Next Chat Template

Copy & paste fuer nahtlosen Session-Uebergang.

**WICHTIG:** Die Handover-Dateien liegen im GitLab Repo, NICHT in /mnt/project/!
Claude muss sie via GitLab API lesen (curl mit PAT).

---

## Aktueller Prompt (2026-02-06)

```
Kontext: NSAI v0.3.0 gemergt. Ontology-MAB Alignment, 85 Tests, Experiment-Notebook mit TestSuite, ADR-027. Heute: JKU Paper Draft und/oder Cloud Run Redeploy.

WICHTIG: Handover-Dateien liegen im GitLab Repo, nicht in /mnt/project/!
Lies via API:
  curl -s --header "PRIVATE-TOKEN: $PAT" \
    "https://gitlab.com/api/v4/projects/77555895/repository/files/docs%2Fhandover%2FINDEX.md/raw?ref=main"

Detail-Handover:
  curl -s --header "PRIVATE-TOKEN: $PAT" \
    "https://gitlab.com/api/v4/projects/77555895/repository/files/docs%2Fhandover%2FHANDOVER_NSAI_V030_06_02_2026.md/raw?ref=main"

Credentials:
- GitLab PAT: glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj
- User: wolfram.laube (ID: 1349601)
- Backoffice Project ID: 77555895
- GCP Project: myk8sproject-207017
- MAB Service: https://runner-bandit-m5cziijwqa-lz.a.run.app/

Repos:
- ops/backoffice (77555895) - Operations + services/nsai/ + services/runner_bandit/
- ops/crm (78171527) - CRM Issues
- ops/corporate (77075415) - Corporate

Offene Themen (Prio):
1. Issue #26: JKU Bachelor Paper Draft — Experiment-Daten stehen bereit
2. Cloud Run Redeploy — GCS Persistence fuer MAB State
3. Lokale Runner aktivieren (Mac, Linux Yoga) fuer Multi-Runner-Daten
4. GitHub Mirror (#29) — Notebook nach GitHub fuer Colab/JKU
5. Bug Cleanup: #41, #42, #34, #43

NSAI = Neurosymbolic AI (CSP filter -> MAB optimize), v0.3.0 auf main
MAB = Multi-Armed Bandit (UCB1), Cloud Run, 83 Observations
ADR-027 = Architecture Decision Record (HTML, Dialektik-Format)
```
