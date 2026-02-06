# HANDOVER: NSAI v0.3.0 — Alignment, TestSuite, ADR

**Date:** 2026-02-06
**Session:** NSAI v0.3.0 Development (Abend-Session)
**Author:** Wolfram Laube + Claude

## Was wurde gemacht

### 1. NSAI v0.3.0 — Ontology-MAB Alignment (MR !17, merged)

**Problem:** NSAI-Ontologie hatte Placeholder-Runner (mac-local, linux-local), MAB Service hatte echte Namen (Mac Docker Runner, etc.). Sync war kaputt.

**Loesung:**
- runner_ontology.py: 4 Production-Runner mit mab_tag Mapping
- interface.py: sync_from_mab_service() mit Tag-Resolution, from_live_service() Factory
- Version 0.2.0 -> 0.3.0

**Runner-Mapping:**

| Ontology Name | MAB Tag | GitLab Tags |
|--------------|---------|-------------|
| gitlab-runner-nordic | nordic | docker-any, nordic |
| Mac Docker Runner | mac-docker | docker-any, mac-docker |
| Mac2 Docker Runner | mac2-docker | docker-any, mac2-docker |
| Linux Yoga Docker Runner | linux-docker | docker-any, linux-docker |

### 2. Experiment Notebook mit TestSuite (JKU-Style)

services/nsai/notebooks/nsai_experiment.ipynb — 13 TestSuite-Cells, jede Section validiert sich selbst via assert.

| Section | Prueft |
|---------|--------|
| Setup | Version >= 0.3.0, 4 Runner, Tag-Roundtrip |
| Ground Truth | Ontologie-Alignment, Reward-Monotonie, Determinismus |
| Strategies | Rule-Based statisch, MAB exploriert alle, NSAI valide |
| Experiment | 300 Rounds, monotone Rewards, Determinismus |
| Reward | NSAI > Rule-Based, NSAI/MAB >= 80%, Regret-Vergleich |
| Distribution | Learner favorisieren Linux Yoga, vermeiden Mac2 |
| Convergence | MAB+NSAI < 200 Rounds, Regret sublinear |
| GCP Constraint | NSAI nur nordic, weniger Failures als MAB |
| Live MAB | UCB1, 4 Runner, Stats-Ranges, Sync-Konsistenz |
| Explanations | Feasible counts, Impossible->None, Serialisierung |
| Performance | Select < 5ms, Update < 1ms |
| Final Gate | 10 Kern-Invarianten zusammengefasst |

Fix: PureMABStrategy.select() Test brauchte interleaved select+update (fb36288c).

### 3. Integration Tests

services/nsai/tests/test_nsai_integration.py — 25 Tests in 6 Klassen.
Gesamt: 85 Tests, alle gruen.

### 4. ADR-027 NSAI Architecture

docs/adr/ADR-027-nsai-architecture.html — Promoted von nsai-overview.html.
Dialektische Struktur = natuerliches ADR-Format. Visuelles Design unverändert.

### 5. ADR Index

docs/adr/README.md — Uebersicht aller ADRs (ADR-027, ADR-030, OPS-001).

### 6. Issue #47 (CI Quota Failures)

Aufgemacht, untersucht, dokumentiert, geschlossen. Problem nur auf Feature Branch.

## Commits

| Commit | Beschreibung |
|--------|-------------|
| 05371978 | feat(nsai): v0.3.0 — MAB alignment, integration tests, experiment notebook |
| fb36288c | fix(nsai): notebook strategy test — interleave select+update |
| 316bf6e6 | docs(adr): ADR-027 NSAI Architecture |
| 1e041542 | docs(adr): add ADR index README |
| f37c2953 | Merge commit MR !17 |

## MAB Service

- URL: https://runner-bandit-m5cziijwqa-lz.a.run.app
- Observations: 83 (nur nordic), Webhooks aktiv
- GCS Persistence: Noch nicht deployed

## Naechste Schritte

1. Issue #26: JKU Bachelor Paper Draft
2. Cloud Run Redeploy mit GCS Backend
3. Lokale Runner aktivieren (Mac, Linux Yoga)
4. GitHub Mirror (#29) fuer Colab/JKU
5. Bug Cleanup: #41, #42, #34, #43

## Keywords

nsai, v0.3.0, mab, alignment, ontology, mab-tag, integration-test, experiment, notebook, testsuite, convergence, regret, ucb1, adr, adr-027, runner-mapping, live-sync, jku
