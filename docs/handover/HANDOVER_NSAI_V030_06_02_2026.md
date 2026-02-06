# HANDOVER: NSAI v0.3.0 — MAB Alignment & Experiment Framework

**Datum:** 2026-02-06
**Session:** NSAI v0.3.0 Release
**Vorherige Session:** NSAI Interface Implementation (2026-02-05)

---

## 🎯 Executive Summary

**Ziel:** NSAI-Ontologie mit MAB Service alignen, Integration testen, Experiment-Framework aufbauen.

**Ergebnis:** v0.3.0 released als MR !17 mit:
- ✅ Ontologie: 4 Runner aligned mit MAB Service + `mab_tag` Mapping
- ✅ 25 neue Integration-Tests (A/B, Live MAB, Convergence, Regret)
- ✅ Experiment-Notebook mit reproduzierbaren 300-Round A/B-Vergleichen
- ✅ 85/85 Tests grün (inkl. Live-MAB-Tests)
- 🔧 Cloud Run GCS-Redeploy: Pipeline getriggert, wartet auf Runner

---

## 📊 Experiment-Ergebnisse (300 Rounds, docker-any)

| Strategie | Cum. Reward | Cum. Regret | Konvergenz |
|-----------|-------------|-------------|------------|
| Pure MAB | 820.6 | ~15 | Round 17 |
| **NSAI** | 787.6 | ~27 | Round 77 |
| Rule-Based | 721.3 | ~93 | nie |

**Interpretation:** Für docker-any Jobs (alle 4 Runner feasible) hat Pure MAB leichten Vorteil,
weil CSP-Layer keinen Runner filtert. NSAI-Vorteil zeigt sich bei constraint-intensiven Jobs
(GCP, Shell) wo CSP den Action Space reduziert → schnellere Konvergenz.

---

## 📁 Geänderte Dateien (Commit `05371978`)

| Datei | Aktion | Beschreibung |
|-------|--------|-------------|
| `services/nsai/ontology/runner_ontology.py` | UPDATE | 4 Prod-Runner, mab_tag, Tag-Mapping |
| `services/nsai/interface.py` | UPDATE | sync mit Tag-Resolution, from_live_service() |
| `services/nsai/__init__.py` | UPDATE | Version 0.2.0 → 0.3.0 |
| `services/nsai/tests/test_ontology.py` | UPDATE | Tests für neue Runner-Names |
| `services/nsai/tests/test_nsai_integration.py` | NEW | 25 Integration-Tests |
| `services/nsai/notebooks/nsai_experiment.ipynb` | NEW | A/B Experiment-Notebook |

---

## 🔀 Offene MRs

| MR | Title | Branch | Status |
|----|-------|--------|--------|
| !17 | feat(nsai): v0.3.0 | feature/nsai-v0.3.0-alignment | ⏳ Pipeline |

---

## 🔧 Infrastructure Status

### MAB Service (Cloud Run)
- **URL:** https://runner-bandit-m5cziijwqa-lz.a.run.app
- **Observations:** 13 (nur nordic, lokale Runner noch 0 pulls)
- **GCS Persistence:** Noch nicht aktiv (Redeploy nötig)
- **Deploy Pipeline:** #2311202976 (`cloud-run:build` + `cloud-run:deploy` warten auf Runner)

### Webhooks
| Repo | Webhook | Status |
|------|---------|--------|
| Backoffice | 69840788 | ✅ aktiv (liefert Daten) |
| Portal | 69912322 | ✅ erstellt |
| CLARISSA | 69912323 | ✅ erstellt |

---

## 📋 Nächste Schritte

1. **MR !17 mergen** nach Pipeline-Success
2. **Cloud Run Redeploy** manuell falls Pipeline blockiert:
   ```bash
   gcloud run deploy runner-bandit \
     --image=europe-north1-docker.pkg.dev/myk8sproject-207017/backoffice/runner-bandit:latest \
     --region=europe-north1 \
     --set-env-vars=BANDIT_ALGORITHM=ucb1,BANDIT_GCS_BUCKET=blauweiss-mab-state
   ```
3. **Lokale Runner aktivieren** (Mac, Linux Yoga) → MAB bekommt Daten für alle 4 Runner
4. **Issue #26: JKU Paper Draft** — Experiment-Ergebnisse als Basis
5. **Constraint-intensive A/B Tests** — GCP-only / Shell-only Jobs testen wo NSAI-Vorteil größer
6. **Notebook → Colab** — auf GitHub Mirror pushen für JKU-Dozenten

---

## 💬 Prompt für nächsten Chat

```
Kontext: NSAI v0.3.0 ist als MR !17 offen. Ontologie aligned mit MAB Service,
85 Tests grün, Experiment-Notebook zeigt A/B-Vergleich.

Handover: docs/handover/HANDOVER_NSAI_V030_06_02_2026.md

Offene Tasks:
1. MR !17 reviewen/mergen
2. Cloud Run Redeploy mit GCS (Pipeline #2311202976 oder manuell)
3. Issue #26: JKU Paper Draft (Experiment-Ergebnisse als Basis)
4. Constraint-intensive A/B Tests erweitern
5. NSAI Overview HTML aktualisieren (v0.3.0 Status)

Credentials:
- GitLab PAT: glpat--wmS4xEWjjWdOgaOd7oDWG86MQp1OnN4Y3gK.01.101dpjjbj
- MAB: https://runner-bandit-m5cziijwqa-lz.a.run.app
- GCS: gs://blauweiss-mab-state/bandit_state.json
```

---

## Keywords

nsai, v0.3.0, mab, alignment, ontology, mab-tag, integration-test, a/b, experiment, notebook, convergence, regret, ucb1
